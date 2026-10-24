"""Record the Learning outcome of a confirmed Mentor action on its proposal."""

import asyncio
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar, Literal, Self, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from shifu.intelligence.core.use_cases import RecordMentorActionOutcomeUseCase

LOGGER = logging.getLogger(__name__)


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    account_id: str = Field(min_length=1)
    confirmation_id: str = Field(min_length=1)
    operation: Literal['add_skill', 'remove_skill']
    outcome: Literal['added', 'already_present', 'removed', 'rejected']
    rejection_reason: (
        Literal['goal_unavailable', 'skill_unavailable', 'experience_unavailable']
        | None
    )
    goal_id: str = Field(min_length=1)
    skill_id: str | None
    skill_experience_id: str | None
    resolved_at: str = Field(min_length=1)

    @field_validator('account_id', 'confirmation_id', 'goal_id')
    @classmethod
    def validate_required_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('identifiers must not be empty')
        return value

    @field_validator('skill_id', 'skill_experience_id')
    @classmethod
    def validate_optional_id(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError('identifiers must not be empty')
        return value

    @field_validator('resolved_at')
    @classmethod
    def validate_resolved_at(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError('resolved_at must be an ISO-8601 timestamp') from error
        if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
            raise ValueError('resolved_at must be UTC')
        return value

    @model_validator(mode='after')
    def validate_rejection(self) -> Self:
        if (self.outcome == 'rejected') != (self.rejection_reason is not None):
            raise ValueError(
                'rejection_reason is set exactly when the outcome is rejected'
            )
        return self


def _validate_payload(data: Mapping[str, object]) -> _Payload:
    try:
        return _Payload.model_validate(dict(data))
    except ValidationError as error:
        raise NonRetriableError('Invalid Mentor action outcome payload') from error


class RecordMentorActionOutcomeJob:
    FUNCTION_ID: ClassVar[str] = 'intelligence-record-mentor-action-outcome'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: RecordMentorActionOutcomeUseCase,
        *,
        outcome_event_name: str,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=RecordMentorActionOutcomeJob.FUNCTION_ID,
            trigger=TriggerEvent(event=outcome_event_name),
            retries=3,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            try:
                payload = await context.step.run(
                    'normalize_payload',
                    RecordMentorActionOutcomeJob._normalize_payload,
                    data,
                )
            except NonRetriableError:
                LOGGER.warning(
                    'mentor_action_outcome_payload_rejected event_id=%s',
                    context.event.id,
                )
                raise
            await context.step.run(
                'record_mentor_action_outcome',
                RecordMentorActionOutcomeJob._record,
                use_case,
                payload,
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, str | None]:
        payload = _validate_payload(data)
        return {
            'account_id': payload.account_id,
            'confirmation_id': payload.confirmation_id,
            'operation': payload.operation,
            'outcome': payload.outcome,
            'rejection_reason': payload.rejection_reason,
            'goal_id': payload.goal_id,
            'skill_id': payload.skill_id,
            'skill_experience_id': payload.skill_experience_id,
            'resolved_at': payload.resolved_at,
        }

    @staticmethod
    async def _record(
        use_case: RecordMentorActionOutcomeUseCase, payload: dict[str, str | None]
    ) -> bool:
        return await asyncio.to_thread(
            use_case.execute,
            cast('str', payload['account_id']),
            cast('str', payload['confirmation_id']),
            cast('str', payload['operation']),
            cast('str', payload['outcome']),
            payload['rejection_reason'],
            cast('str', payload['goal_id']),
            payload['skill_id'],
            payload['skill_experience_id'],
        )
