"""Gamification consumer of one due streak reminder."""

import asyncio
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.events import StreakReminderDueEvent
from shifu.gamification.core.domain.reminder_slot_start import (
    require_reminder_slot_start,
)
from shifu.gamification.core.use_cases import RequestStreakReminderUseCase
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)

_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    account_id: str = Field(min_length=1)
    local_date: str = Field(min_length=1)
    slot_start: str = Field(min_length=1)

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('account_id must not be empty')
        return value

    @field_validator('local_date')
    @classmethod
    def validate_local_date(cls, value: str) -> str:
        if _DATE_PATTERN.fullmatch(value) is None:
            raise ValueError('local_date must be an ISO date')
        date.fromisoformat(value)
        return value

    @field_validator('slot_start')
    @classmethod
    def validate_slot_start(cls, value: str) -> str:
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
        raise ValueError('Job event time must be an ISO-8601 string') from error
    if parsed_time.tzinfo is None or parsed_time.utcoffset() != UTC.utcoffset(
        parsed_time
    ):
        raise ValueError('Job event time must be UTC')
    return parsed_time


def _validate_payload(data: Mapping[str, object]) -> _Payload:
    try:
        return _Payload.model_validate(dict(data))
    except ValidationError as error:
        raise NonRetriableError('Invalid streak reminder due event payload') from error


class RequestStreakReminderJob:
    """Re-check eligibility for one due learner and request the reminder."""

    FUNCTION_ID: ClassVar[str] = 'gamification-request-streak-reminder'
    _EVENT_NAME: ClassVar[str] = StreakReminderDueEvent.EVENT_NAME

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: RequestStreakReminderUseCase,
        *,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=RequestStreakReminderJob.FUNCTION_ID,
            trigger=TriggerEvent(event=RequestStreakReminderJob._EVENT_NAME),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=RequestStreakReminderJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            normalized = await context.step.run(
                'normalize_payload',
                RequestStreakReminderJob._normalize_payload,
                data,
            )
            await context.step.run(
                'request_streak_reminder',
                RequestStreakReminderJob._request_streak_reminder,
                use_case,
                normalized['account_id'],
                normalized['slot_start'],
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, str]:
        payload = _validate_payload(data)
        return {'account_id': payload.account_id, 'slot_start': payload.slot_start}

    @staticmethod
    async def _request_streak_reminder(
        use_case: RequestStreakReminderUseCase,
        account_id: str,
        slot_start: str,
    ) -> bool:
        return await asyncio.to_thread(
            use_case.execute,
            account_id,
            slot_start=_parse_utc_iso(slot_start),
        )
