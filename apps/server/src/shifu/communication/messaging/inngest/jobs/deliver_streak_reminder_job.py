"""Durable streak reminder delivery with persisted retry scheduling."""

import asyncio
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from typing import ClassVar, TypedDict, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    field_validator,
)

from shifu.communication.core.domain.entities import StreakReminder
from shifu.communication.core.domain.enums import StreakReminderStatus
from shifu.communication.core.domain.structures import StreakReminderRequest
from shifu.communication.core.use_cases import (
    DeliverStreakReminderUseCase,
    QueueStreakReminderUseCase,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)

_LOCAL_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class _Payload(BaseModel):
    """Local wire contract; it intentionally does not import Gamification core."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    account_id: str = Field(min_length=1)
    local_date: str
    streak_days: StrictInt = Field(ge=1)
    expires_at: str

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('account_id must not be empty')
        return value

    @field_validator('local_date')
    @classmethod
    def validate_local_date(cls, value: str) -> str:
        if _LOCAL_DATE_PATTERN.fullmatch(value) is None:
            raise ValueError('local_date must be an ISO date')
        date.fromisoformat(value)
        return value

    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError('expires_at must be a UTC instant')
        return value


def _validate_payload(data: Mapping[str, object]) -> _Payload:
    try:
        return _Payload.model_validate(dict(data))
    except ValidationError as error:
        raise NonRetriableError(
            'Invalid streak reminder requested event payload'
        ) from error


class _ReminderResult(TypedDict):
    status: str
    next_attempt_at: str | None


class DeliverStreakReminderJob:
    """Queue the daily reminder, then attempt delivery until it is terminal."""

    FUNCTION_ID: ClassVar[str] = 'communication-deliver-streak-reminder'
    _MAX_DELIVERY_ATTEMPTS: ClassVar[int] = 64

    @staticmethod
    def handle(
        inngest: Inngest,
        queue_use_case: QueueStreakReminderUseCase,
        deliver_use_case: DeliverStreakReminderUseCase,
        *,
        streak_reminder_requested_event_name: str,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=DeliverStreakReminderJob.FUNCTION_ID,
            trigger=TriggerEvent(event=streak_reminder_requested_event_name),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=DeliverStreakReminderJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            request = await context.step.run(
                'normalize_payload',
                DeliverStreakReminderJob._normalize_payload,
                data,
            )
            queued = await context.step.run(
                'queue_streak_reminder',
                DeliverStreakReminderJob._queue_streak_reminder,
                queue_use_case,
                request,
            )
            reminder_id = queued['reminder_id']
            result: _ReminderResult = {
                'status': queued['status'],
                'next_attempt_at': None,
            }

            for attempt_number in range(
                1, DeliverStreakReminderJob._MAX_DELIVERY_ATTEMPTS + 1
            ):
                if result['status'] != StreakReminderStatus.PENDING.value:
                    return
                if attempt_number > 1:
                    next_attempt_at = result['next_attempt_at']
                    if next_attempt_at is None:
                        return
                    await context.step.sleep_until(
                        f'wait_for_attempt_{attempt_number}',
                        DeliverStreakReminderJob._parse_schedule(next_attempt_at),
                    )
                attempt = await context.step.run(
                    f'deliver_attempt_{attempt_number}',
                    DeliverStreakReminderJob._deliver_attempt,
                    deliver_use_case,
                    reminder_id,
                )
                if attempt is None:
                    return
                result = attempt

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, object]:
        payload = _validate_payload(data)
        return {
            'account_id': payload.account_id,
            'local_date': payload.local_date,
            'streak_days': payload.streak_days,
            'expires_at': (
                datetime.fromisoformat(payload.expires_at).astimezone(UTC).isoformat()
            ),
        }

    @staticmethod
    async def _queue_streak_reminder(
        use_case: QueueStreakReminderUseCase,
        payload: Mapping[str, object],
    ) -> dict[str, str]:
        request = StreakReminderRequest(
            account_id=str(payload['account_id']),
            local_date=date.fromisoformat(str(payload['local_date'])),
            streak_days=int(cast('int', payload['streak_days'])),
            expires_at=datetime.fromisoformat(str(payload['expires_at'])),
        )
        reminder = await asyncio.to_thread(use_case.execute, request)
        return {'reminder_id': reminder.id, 'status': reminder.status.value}

    @staticmethod
    async def _deliver_attempt(
        use_case: DeliverStreakReminderUseCase,
        reminder_id: str,
    ) -> _ReminderResult | None:
        reminder = await asyncio.to_thread(use_case.execute, reminder_id)
        return DeliverStreakReminderJob._serialize_result(reminder)

    @staticmethod
    def _serialize_result(reminder: StreakReminder | None) -> _ReminderResult | None:
        if reminder is None:
            return None
        return {
            'status': reminder.status.value,
            'next_attempt_at': (
                reminder.next_attempt_at.isoformat()
                if reminder.next_attempt_at is not None
                else None
            ),
        }

    @staticmethod
    def _parse_schedule(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError('Streak reminder retry schedule must be timezone-aware')
        return parsed
