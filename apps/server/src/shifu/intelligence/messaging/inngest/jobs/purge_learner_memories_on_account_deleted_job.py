"""Purge private learner memories as soon as an account is deleted."""

import asyncio
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.intelligence.core.use_cases import PurgeLearnerMemoriesForAccountUseCase

LOGGER = logging.getLogger(__name__)


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    account_id: str = Field(min_length=1)
    deleted_at: str = Field(min_length=1)

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('account_id must not be empty')
        return value

    @field_validator('deleted_at')
    @classmethod
    def validate_deleted_at(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError('deleted_at must be an ISO-8601 timestamp') from error
        if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
            raise ValueError('deleted_at must be UTC')
        return value


def _validate_payload(data: Mapping[str, object]) -> _Payload:
    try:
        return _Payload.model_validate(dict(data))
    except ValidationError as error:
        raise NonRetriableError('Invalid account deletion event payload') from error


class PurgeLearnerMemoriesOnAccountDeletedJob:
    FUNCTION_ID: ClassVar[str] = (
        'intelligence-purge-learner-memories-on-account-deleted'
    )

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: PurgeLearnerMemoriesForAccountUseCase,
        *,
        account_deleted_event_name: str,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=PurgeLearnerMemoriesOnAccountDeletedJob.FUNCTION_ID,
            trigger=TriggerEvent(event=account_deleted_event_name),
            retries=3,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            try:
                payload = await context.step.run(
                    'normalize_payload',
                    PurgeLearnerMemoriesOnAccountDeletedJob._normalize_payload,
                    data,
                )
            except NonRetriableError:
                LOGGER.warning(
                    'learner_memory_account_deletion_payload_rejected event_id=%s',
                    context.event.id,
                )
                raise
            await context.step.run(
                'purge_learner_memories',
                PurgeLearnerMemoriesOnAccountDeletedJob._purge,
                use_case,
                payload['account_id'],
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, str]:
        payload = _validate_payload(data)
        return {'account_id': payload.account_id, 'deleted_at': payload.deleted_at}

    @staticmethod
    async def _purge(
        use_case: PurgeLearnerMemoriesForAccountUseCase, account_id: str
    ) -> int:
        return await asyncio.to_thread(use_case.execute, account_id)
