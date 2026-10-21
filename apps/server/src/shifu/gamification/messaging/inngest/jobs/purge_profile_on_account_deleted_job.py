"""Gamification consumer for Identity account-deletion events."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.gamification.core.use_cases import DeleteGamificationProfileUseCase


class _Payload(BaseModel):
    """Local wire contract; it intentionally does not import Identity core."""

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
        raise NonRetriableError('Invalid account deletion event payload') from error


class PurgeProfileOnAccountDeletedJob:
    """Purge every Gamification row for the account, on account deletion."""

    FUNCTION_ID: ClassVar[str] = 'gamification-purge-profile-on-account-deleted'
    _EVENT_NAME: ClassVar[str] = 'identity/account.deleted'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: DeleteGamificationProfileUseCase,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=PurgeProfileOnAccountDeletedJob.FUNCTION_ID,
            trigger=TriggerEvent(event=PurgeProfileOnAccountDeletedJob._EVENT_NAME),
            retries=3,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            account_id = await context.step.run(
                'normalize_payload',
                PurgeProfileOnAccountDeletedJob._normalize_payload,
                data,
            )
            await context.step.run(
                'purge_gamification_profile',
                PurgeProfileOnAccountDeletedJob._purge_profile,
                use_case,
                account_id,
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> str:
        payload = _validate_payload(data)
        return payload.account_id

    @staticmethod
    async def _purge_profile(
        use_case: DeleteGamificationProfileUseCase,
        account_id: str,
    ) -> None:
        await asyncio.to_thread(use_case.execute, account_id)
