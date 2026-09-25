"""Communication consumer for Identity confirmation cancellation events."""

import asyncio
from collections.abc import Mapping
from typing import ClassVar, Literal, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.communication.core.use_cases import CancelCommunicationUseCase


class _Payload(BaseModel):
    """Local wire contract; it intentionally does not import Identity core."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    communication_id: str = Field(min_length=1)
    identity_confirmation_id: str = Field(min_length=1)
    reason: Literal['confirmed', 'reissued', 'expired']

    @field_validator('communication_id', 'identity_confirmation_id')
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Identifier must not be empty')
        return value


def _validate_payload(data: Mapping[str, object]) -> _Payload:
    try:
        return _Payload.model_validate(dict(data))
    except ValidationError as error:
        raise NonRetriableError('Invalid account cancellation event payload') from error


class CancelCommunicationJob:
    """Stop or redact one correlated Communication request idempotently."""

    FUNCTION_ID: ClassVar[str] = 'communication-cancel'
    _EVENT_NAME: ClassVar[str] = 'identity.account-confirmation-cancelled'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: CancelCommunicationUseCase,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=CancelCommunicationJob.FUNCTION_ID,
            trigger=TriggerEvent(event=CancelCommunicationJob._EVENT_NAME),
            retries=3,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            normalized_data = await context.step.run(
                'normalize_payload',
                CancelCommunicationJob._normalize_payload,
                data,
            )
            await context.step.run(
                'cancel_communication',
                CancelCommunicationJob._cancel_communication,
                use_case,
                normalized_data,
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, str]:
        payload = _validate_payload(data)
        return {
            'communication_id': payload.communication_id,
            'identity_confirmation_id': payload.identity_confirmation_id,
            'reason': payload.reason,
        }

    @staticmethod
    async def _cancel_communication(
        use_case: CancelCommunicationUseCase,
        payload: Mapping[str, str],
    ) -> bool:
        return await asyncio.to_thread(
            use_case.execute,
            payload['communication_id'],
            payload['identity_confirmation_id'],
            payload['reason'],
        )
