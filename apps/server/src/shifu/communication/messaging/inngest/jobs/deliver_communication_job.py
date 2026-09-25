"""Durable Communication delivery with persisted retry scheduling."""

import asyncio
from collections.abc import Mapping
from datetime import datetime
from typing import ClassVar, TypedDict, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.communication.core.domain.entities import Communication
from shifu.communication.core.domain.enums import CommunicationStatus
from shifu.communication.core.domain.events import (
    CommunicationQueuedEvent,
    CommunicationQueuedPayload,
)
from shifu.communication.core.use_cases import DeliverCommunicationUseCase


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    communication_id: str = Field(min_length=1)

    @field_validator('communication_id')
    @classmethod
    def validate_communication_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Communication ID must not be empty')
        return value


def _validate_payload(data: Mapping[str, object]) -> _Payload:
    try:
        return _Payload.model_validate(dict(data))
    except ValidationError as error:
        raise NonRetriableError('Invalid communication queued event payload') from error


class _DeliveryResult(TypedDict):
    status: str
    next_attempt_at: str | None
    attempt_count: int


class DeliverCommunicationJob:
    """Run at most five provider attempts for one stable communication ID."""

    FUNCTION_ID: ClassVar[str] = 'communication-deliver'
    _EVENT_NAME: ClassVar[str] = CommunicationQueuedEvent(
        payload=CommunicationQueuedPayload(communication_id='transport')
    ).name
    _MAX_ATTEMPTS: ClassVar[int] = DeliverCommunicationUseCase.MAX_ATTEMPTS

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: DeliverCommunicationUseCase,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=DeliverCommunicationJob.FUNCTION_ID,
            trigger=TriggerEvent(event=DeliverCommunicationJob._EVENT_NAME),
            retries=3,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            normalized_data = await context.step.run(
                'normalize_payload',
                DeliverCommunicationJob._normalize_payload,
                data,
            )

            for attempt_number in range(1, DeliverCommunicationJob._MAX_ATTEMPTS + 1):
                result = await context.step.run(
                    f'deliver_attempt_{attempt_number}',
                    DeliverCommunicationJob._deliver_attempt,
                    use_case,
                    normalized_data['communication_id'],
                )
                if result is None:
                    return
                if result['status'] != CommunicationStatus.PENDING.value:
                    return
                next_attempt_at = result['next_attempt_at']
                if next_attempt_at is None or attempt_number == (
                    DeliverCommunicationJob._MAX_ATTEMPTS
                ):
                    return
                await context.step.sleep_until(
                    f'wait_for_attempt_{attempt_number + 1}',
                    DeliverCommunicationJob._parse_schedule(next_attempt_at),
                )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, str]:
        payload = _validate_payload(data)
        return {'communication_id': payload.communication_id}

    @staticmethod
    async def _deliver_attempt(
        use_case: DeliverCommunicationUseCase,
        communication_id: str,
    ) -> _DeliveryResult | None:
        communication = await asyncio.to_thread(use_case.execute, communication_id)
        return DeliverCommunicationJob._serialize_result(communication)

    @staticmethod
    def _serialize_result(
        communication: Communication | None,
    ) -> _DeliveryResult | None:
        if communication is None:
            return None
        return {
            'status': communication.status.value,
            'next_attempt_at': (
                communication.next_attempt_at.isoformat()
                if communication.next_attempt_at is not None
                else None
            ),
            'attempt_count': communication.attempt_count,
        }

    @staticmethod
    def _parse_schedule(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError('Communication retry schedule must be timezone-aware')
        return parsed
