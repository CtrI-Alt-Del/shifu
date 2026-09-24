"""Durable consumer for one pending-account expiry request."""

import asyncio
from collections.abc import Mapping
from typing import ClassVar, cast

from inngest import (
    Concurrency,
    Context,
    Function,
    Inngest,
    NonRetriableError,
    TriggerEvent,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.identity.core.domain.events import (
    AccountExpiryRequestedEvent,
    AccountExpiryRequestedPayload,
)
from shifu.identity.core.use_cases import ExpireUnconfirmedAccountsUseCase


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    account_id: str = Field(min_length=1)

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Account ID must not be empty')
        return value


def _validate_payload(data: Mapping[str, object]) -> _Payload:
    try:
        return _Payload.model_validate(dict(data))
    except ValidationError as error:
        raise NonRetriableError('Invalid account expiry event payload') from error


class ExpireUnconfirmedAccountJob:
    """Apply one expiry transition through the Identity use case."""

    FUNCTION_ID: ClassVar[str] = 'identity-expire-unconfirmed-account'
    _CONCURRENCY_LIMIT: ClassVar[int] = 25
    _EVENT_NAME: ClassVar[str] = AccountExpiryRequestedEvent(
        payload=AccountExpiryRequestedPayload(account_id='transport')
    ).name

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: ExpireUnconfirmedAccountsUseCase,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=ExpireUnconfirmedAccountJob.FUNCTION_ID,
            trigger=TriggerEvent(event=ExpireUnconfirmedAccountJob._EVENT_NAME),
            retries=3,
            concurrency=[
                Concurrency(limit=ExpireUnconfirmedAccountJob._CONCURRENCY_LIMIT)
            ],
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            normalized_data = await context.step.run(
                'normalize_payload',
                ExpireUnconfirmedAccountJob._normalize_payload,
                data,
            )
            await context.step.run(
                'expire_account',
                ExpireUnconfirmedAccountJob._expire_account,
                use_case,
                normalized_data['account_id'],
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, str]:
        payload = _validate_payload(data)
        return {'account_id': payload.account_id}

    @staticmethod
    async def _expire_account(
        use_case: ExpireUnconfirmedAccountsUseCase,
        account_id: str,
    ) -> list[str]:
        expired_account_ids = await asyncio.to_thread(use_case.execute, account_id)
        return list(expired_account_ids)
