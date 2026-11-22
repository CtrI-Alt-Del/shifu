"""Purge private practice drafts and photos after account deletion retention expires."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.learning.core.use_cases import PurgePracticePhotosUseCase
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)


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


class PurgePracticeDataOnAccountDeletedJob:
    FUNCTION_ID: ClassVar[str] = 'learning-purge-practice-data-on-account-deleted'
    _RETENTION: ClassVar[timedelta] = timedelta(hours=24)

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: PurgePracticePhotosUseCase,
        *,
        account_deleted_event_name: str,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=PurgePracticeDataOnAccountDeletedJob.FUNCTION_ID,
            trigger=TriggerEvent(event=account_deleted_event_name),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=PurgePracticeDataOnAccountDeletedJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            payload = await context.step.run(
                'normalize_payload',
                PurgePracticeDataOnAccountDeletedJob._normalize_payload,
                data,
            )
            purge_after = datetime.fromisoformat(payload['deleted_at']) + (
                PurgePracticeDataOnAccountDeletedJob._RETENTION
            )
            await context.step.sleep_until('account_retention_period', purge_after)
            await context.step.run(
                'purge_practice_data',
                PurgePracticeDataOnAccountDeletedJob._purge,
                use_case,
                payload['account_id'],
            )

        return _

    @staticmethod
    async def _normalize_payload(data: Mapping[str, object]) -> dict[str, str]:
        try:
            payload = _Payload.model_validate(dict(data))
        except ValidationError as error:
            raise NonRetriableError('Invalid account deletion event payload') from error

        return {'account_id': payload.account_id, 'deleted_at': payload.deleted_at}

    @staticmethod
    async def _purge(use_case: PurgePracticePhotosUseCase, account_id: str) -> None:
        await asyncio.to_thread(use_case.execute_for_deleted_account, account_id)
