"""Every-15-minutes fan-out of learners whose reminder hour starts at the slot."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerCron
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.reminder_slot_start import (
    SLOT_MINUTES,
    require_reminder_slot_start,
)
from shifu.gamification.core.use_cases import FanOutDueStreakRemindersUseCase
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)

_SLOT_MILLISECONDS = SLOT_MINUTES * 60 * 1000


class _Invocation(BaseModel):
    """The only field this job reads from its invocation data.

    A scheduled run carries the cron expression instead, so unknown fields are
    ignored. An explicit `slot_start` takes precedence over the scheduled time
    and must be an aligned UTC instant.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='ignore',
        frozen=True,
        strict=True,
    )

    slot_start: str | None = None

    @field_validator('slot_start')
    @classmethod
    def validate_slot_start(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = _parse_utc_iso(value)
        try:
            require_reminder_slot_start(parsed)
        except InvalidGamificationError as error:
            raise ValueError('slot_start must be aligned to the slot') from error
        return value


def _parse_utc_iso(value: str) -> datetime:
    try:
        parsed_time = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError('slot_start must be an ISO-8601 string') from error
    if parsed_time.tzinfo is None or parsed_time.utcoffset() != UTC.utcoffset(
        parsed_time
    ):
        raise ValueError('slot_start must be UTC')
    return parsed_time


def _format_slot(slot_start: datetime) -> str:
    return slot_start.astimezone(UTC).isoformat().replace('+00:00', 'Z')


class FanOutDueStreakRemindersJob:
    """Walk every reminder candidate for one slot, one durable step per page."""

    FUNCTION_ID: ClassVar[str] = 'gamification-fan-out-due-streak-reminders'
    _CRON: ClassVar[str] = '*/15 * * * *'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: FanOutDueStreakRemindersUseCase,
        *,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=FanOutDueStreakRemindersJob.FUNCTION_ID,
            trigger=TriggerCron(cron=FanOutDueStreakRemindersJob._CRON),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=FanOutDueStreakRemindersJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            scheduled_at = context.event.ts
            slot_start = await context.step.run(
                'resolve_slot',
                FanOutDueStreakRemindersJob._resolve_slot,
                data,
                scheduled_at,
            )

            cursor: str | None = None
            page_index = 0
            while True:
                page = await context.step.run(
                    f'fan_out_page_{page_index}',
                    FanOutDueStreakRemindersJob._fan_out_page,
                    use_case,
                    slot_start,
                    cursor,
                )
                cursor = cast('str | None', page['next_cursor'])
                if cursor is None:
                    return
                page_index += 1

        return _

    @staticmethod
    async def _resolve_slot(data: Mapping[str, object], scheduled_at: int) -> str:
        """Fix the slot once, so every retry evaluates the same window.

        The slot comes from the run's scheduled timestamp, never from the
        execution clock.
        """
        try:
            invocation = _Invocation.model_validate(dict(data))
        except ValidationError as error:
            raise NonRetriableError('Invalid streak reminder slot') from error

        if invocation.slot_start is not None:
            return _format_slot(_parse_utc_iso(invocation.slot_start))

        if scheduled_at <= 0:
            raise NonRetriableError('Missing scheduled time for the slot')
        floored = scheduled_at - scheduled_at % _SLOT_MILLISECONDS
        return _format_slot(datetime.fromtimestamp(floored / 1000, tz=UTC))

    @staticmethod
    async def _fan_out_page(
        use_case: FanOutDueStreakRemindersUseCase,
        slot_start: str,
        cursor: str | None,
    ) -> dict[str, object]:
        page = await asyncio.to_thread(
            use_case.execute,
            _parse_utc_iso(slot_start),
            after_account_id=cursor,
        )
        return {'due_count': page.due_count, 'next_cursor': page.next_cursor}
