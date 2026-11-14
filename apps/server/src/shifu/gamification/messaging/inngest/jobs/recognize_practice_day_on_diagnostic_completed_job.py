"""Gamification consumer recognizing a practice day from a completed diagnostic."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.gamification.core.use_cases import RecognizePracticeDayUseCase
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)
from shifu.shared.core.interfaces import ClockProvider


class _Payload(BaseModel):
    """Local wire contract; it intentionally does not import Learning core."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    account_id: str = Field(min_length=1)
    goal_id: str = Field(min_length=1)
    skill_experience_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    initial_progress: str = Field(min_length=1)
    completed_at: str = Field(min_length=1)
    submitted_at: str = Field(min_length=1)
    # No `min_length`: an absent or empty zone is normalized to UTC by the use
    # case. Rejecting it here would non-retriably discard a real practice day.
    time_zone: str | None = None

    @field_validator('account_id')
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Identifier must not be empty')
        return value

    @field_validator('submitted_at')
    @classmethod
    def validate_submitted_at(cls, value: str) -> str:
        _parse_utc_iso(value)
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
        raise NonRetriableError(
            'Invalid diagnostic completion event payload'
        ) from error


class RecognizePracticeDayOnDiagnosticCompletedJob:
    """Recognize the practice day of the attempt that completed a diagnostic."""

    FUNCTION_ID: ClassVar[str] = (
        'gamification-recognize-practice-day-on-diagnostic-completed'
    )
    _EVENT_NAME: ClassVar[str] = 'learning/diagnostic-completed'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: RecognizePracticeDayUseCase,
        clock_provider: ClockProvider,
        *,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=RecognizePracticeDayOnDiagnosticCompletedJob.FUNCTION_ID,
            trigger=TriggerEvent(
                event=RecognizePracticeDayOnDiagnosticCompletedJob._EVENT_NAME
            ),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=RecognizePracticeDayOnDiagnosticCompletedJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            normalized = await context.step.run(
                'normalize_payload',
                RecognizePracticeDayOnDiagnosticCompletedJob._normalize_payload,
                data,
            )
            await context.step.run(
                'recognize_practice_day',
                RecognizePracticeDayOnDiagnosticCompletedJob._recognize,
                use_case,
                clock_provider,
                normalized,
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, str | None]:
        payload = _validate_payload(data)
        return {
            'account_id': payload.account_id,
            'submitted_at': payload.submitted_at,
            'time_zone': payload.time_zone,
        }

    @staticmethod
    async def _recognize(
        use_case: RecognizePracticeDayUseCase,
        clock_provider: ClockProvider,
        normalized: Mapping[str, str | None],
    ) -> None:
        account_id = normalized['account_id'] or ''
        submitted_at = normalized['submitted_at'] or ''
        await asyncio.to_thread(
            use_case.execute,
            account_id,
            practiced_at=_parse_utc_iso(submitted_at),
            time_zone=normalized['time_zone'],
            now=clock_provider.now(),
        )
