"""Gamification consumer for Learning skill-completion events."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.gamification.core.use_cases import RecognizeSkillCompletedUseCase
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
    final_progress: str = Field(min_length=1)
    completed_at: str = Field(min_length=1)

    @field_validator('account_id', 'goal_id', 'skill_experience_id', 'skill_id')
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Identifier must not be empty')
        return value

    @field_validator('completed_at')
    @classmethod
    def validate_completed_at(cls, value: str) -> str:
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
        raise NonRetriableError('Invalid skill completion event payload') from error


class RecognizeSkillCompletedJob:
    """Grant XP the first time a Habilidade is completed for an account."""

    FUNCTION_ID: ClassVar[str] = 'gamification-recognize-skill-completed'
    _EVENT_NAME: ClassVar[str] = 'learning/skill-completed'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: RecognizeSkillCompletedUseCase,
        clock_provider: ClockProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=RecognizeSkillCompletedJob.FUNCTION_ID,
            trigger=TriggerEvent(event=RecognizeSkillCompletedJob._EVENT_NAME),
            retries=3,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            normalized = await context.step.run(
                'normalize_payload',
                RecognizeSkillCompletedJob._normalize_payload,
                data,
            )
            await context.step.run(
                'recognize_skill_completed',
                RecognizeSkillCompletedJob._recognize,
                use_case,
                clock_provider,
                normalized,
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, str]:
        payload = _validate_payload(data)
        return {
            'account_id': payload.account_id,
            'skill_id': payload.skill_id,
            'skill_experience_id': payload.skill_experience_id,
            'completed_at': payload.completed_at,
        }

    @staticmethod
    async def _recognize(
        use_case: RecognizeSkillCompletedUseCase,
        clock_provider: ClockProvider,
        normalized: Mapping[str, str],
    ) -> None:
        await asyncio.to_thread(
            use_case.execute,
            normalized['account_id'],
            normalized['skill_id'],
            normalized['skill_experience_id'],
            occurred_at=_parse_utc_iso(normalized['completed_at']),
            now=clock_provider.now(),
        )
