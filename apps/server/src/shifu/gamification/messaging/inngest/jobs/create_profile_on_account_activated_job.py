"""Gamification consumer for Identity account-activation events."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.gamification.core.use_cases import CreateGamificationProfileUseCase
from shifu.shared.core.interfaces import ClockProvider


class _Payload(BaseModel):
    """Local wire contract; it intentionally does not import Identity core."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    account_id: str = Field(min_length=1)
    activated_at: str = Field(min_length=1)

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('account_id must not be empty')
        return value

    @field_validator('activated_at')
    @classmethod
    def validate_activated_at(cls, value: str) -> str:
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
        raise NonRetriableError('Invalid account activation event payload') from error


class CreateProfileOnAccountActivatedJob:
    """Create the account's Gamification profile idempotently, on activation."""

    FUNCTION_ID: ClassVar[str] = 'gamification-create-profile-on-account-activated'
    _EVENT_NAME: ClassVar[str] = 'identity/account.activated'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: CreateGamificationProfileUseCase,
        clock_provider: ClockProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=CreateProfileOnAccountActivatedJob.FUNCTION_ID,
            trigger=TriggerEvent(event=CreateProfileOnAccountActivatedJob._EVENT_NAME),
            retries=3,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            account_id = await context.step.run(
                'normalize_payload',
                CreateProfileOnAccountActivatedJob._normalize_payload,
                data,
            )
            await context.step.run(
                'create_gamification_profile',
                CreateProfileOnAccountActivatedJob._create_profile,
                use_case,
                clock_provider,
                account_id,
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> str:
        payload = _validate_payload(data)
        return payload.account_id

    @staticmethod
    async def _create_profile(
        use_case: CreateGamificationProfileUseCase,
        clock_provider: ClockProvider,
        account_id: str,
    ) -> None:
        await asyncio.to_thread(
            use_case.execute,
            account_id,
            now=clock_provider.now(),
        )
