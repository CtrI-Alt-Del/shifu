"""Identity consumer for safe Communication delivery-state projections."""

import asyncio
from collections.abc import Mapping
from typing import ClassVar, Literal, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.identity.core.use_cases import RecordCommunicationDeliveryStateUseCase


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    communication_id: str = Field(min_length=1)
    identity_confirmation_id: str = Field(min_length=1)
    state: Literal[
        'delivered',
        'temporary_failure',
        'permanent_failure',
        'exhausted',
        'cancelled',
    ]

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
        raise NonRetriableError(
            'Invalid communication delivery-state event payload'
        ) from error


class RecordCommunicationDeliveryStateJob:
    """Record only the correlated, safe delivery state in Identity."""

    FUNCTION_ID: ClassVar[str] = 'identity-record-communication-delivery-state'
    _EVENT_NAME: ClassVar[str] = 'communication.delivery-state-changed'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: RecordCommunicationDeliveryStateUseCase,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=RecordCommunicationDeliveryStateJob.FUNCTION_ID,
            trigger=TriggerEvent(event=RecordCommunicationDeliveryStateJob._EVENT_NAME),
            retries=3,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            normalized_data = await context.step.run(
                'normalize_payload',
                RecordCommunicationDeliveryStateJob._normalize_payload,
                data,
            )
            await context.step.run(
                'record_delivery_state',
                RecordCommunicationDeliveryStateJob._record_delivery_state,
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
            'state': payload.state,
        }

    @staticmethod
    async def _record_delivery_state(
        use_case: RecordCommunicationDeliveryStateUseCase,
        payload: Mapping[str, str],
    ) -> bool:
        return await asyncio.to_thread(
            use_case.execute,
            payload['communication_id'],
            payload['identity_confirmation_id'],
            payload['state'],
        )
