"""Gamification consumer producing Activity XP from an evaluated Activity."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.gamification.core.use_cases import RecognizeActivityEvaluatedUseCase
from shifu.shared.core.interfaces import ClockProvider

_VALID_DIFFICULTIES = frozenset({'easy', 'medium', 'hard'})


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
    competency_id: str = Field(min_length=1)
    activity_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    evaluation_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    score: str = Field(min_length=1)
    evaluated_at: str = Field(min_length=1)
    submitted_at: str = Field(min_length=1)
    time_zone: str | None = None

    @field_validator('account_id')
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Identifier must not be empty')
        return value

    @field_validator('difficulty')
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        if value not in _VALID_DIFFICULTIES:
            raise ValueError('Activity difficulty must be easy, medium or hard')
        return value

    @field_validator('score')
    @classmethod
    def validate_score(cls, value: str) -> str:
        _parse_score(value)
        return value

    @field_validator('evaluated_at')
    @classmethod
    def validate_evaluated_at(cls, value: str) -> str:
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


def _parse_score(value: str) -> Decimal:
    try:
        score = Decimal(value)
    except InvalidOperation as error:
        raise ValueError('Activity score must be a decimal number') from error
    if not score.is_finite() or not Decimal(0) <= score <= Decimal(100):
        raise ValueError('Activity score must be between 0 and 100')
    return score


def _validate_payload(data: Mapping[str, object]) -> _Payload:
    try:
        return _Payload.model_validate(dict(data))
    except ValidationError as error:
        raise NonRetriableError('Invalid activity evaluation event payload') from error


class RecognizeActivityXpOnActivityEvaluatedJob:
    """Grant the account's Activity XP when an Activity evaluation lands."""

    FUNCTION_ID: ClassVar[str] = (
        'gamification-recognize-activity-xp-on-activity-evaluated'
    )
    _EVENT_NAME: ClassVar[str] = 'learning/activity-evaluated'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: RecognizeActivityEvaluatedUseCase,
        clock_provider: ClockProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=RecognizeActivityXpOnActivityEvaluatedJob.FUNCTION_ID,
            trigger=TriggerEvent(
                event=RecognizeActivityXpOnActivityEvaluatedJob._EVENT_NAME
            ),
            retries=3,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            normalized = await context.step.run(
                'normalize_payload',
                RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload,
                data,
            )
            await context.step.run(
                'recognize_activity_xp',
                RecognizeActivityXpOnActivityEvaluatedJob._recognize,
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
            'goal_id': payload.goal_id,
            'skill_experience_id': payload.skill_experience_id,
            'activity_id': payload.activity_id,
            'attempt_id': payload.attempt_id,
            'difficulty': payload.difficulty,
            'score': payload.score,
            'evaluated_at': payload.evaluated_at,
        }

    @staticmethod
    async def _recognize(
        use_case: RecognizeActivityEvaluatedUseCase,
        clock_provider: ClockProvider,
        normalized: Mapping[str, str | None],
    ) -> None:
        await asyncio.to_thread(
            use_case.execute,
            normalized['account_id'] or '',
            normalized['activity_id'] or '',
            normalized['attempt_id'] or '',
            normalized['goal_id'] or '',
            normalized['skill_experience_id'] or '',
            difficulty=normalized['difficulty'] or '',
            score=_parse_score(normalized['score'] or ''),
            occurred_at=_parse_utc_iso(normalized['evaluated_at'] or ''),
            now=clock_provider.now(),
        )
