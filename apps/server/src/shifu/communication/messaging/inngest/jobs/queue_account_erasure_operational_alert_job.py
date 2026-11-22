"""Queue a fixed operational notice for one stable account-erasure incident."""

import asyncio
from collections.abc import Mapping
from datetime import datetime
from typing import ClassVar, Literal, cast
from uuid import UUID

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures import (
    AccountErasureOperationalAlertValues,
)
from shifu.communication.core.use_cases import (
    QueueAccountErasureOperationalAlertUseCase,
)
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

    erasure_id: str = Field(min_length=1, max_length=36)
    module: Literal[
        'identity', 'learning', 'gamification', 'intelligence', 'communication'
    ]
    failure_code: Literal['erasure_deadline_exceeded']
    closed_at: str = Field(min_length=1, max_length=64)
    due_at: str = Field(min_length=1, max_length=64)
    incident_id: str = Field(min_length=1, max_length=36)


class QueueAccountErasureOperationalAlertJob:
    """Persist one fixed-template alert; delivery remains owned by the queue job."""

    FUNCTION_ID: ClassVar[str] = 'communication-queue-account-erasure-alert'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: QueueAccountErasureOperationalAlertUseCase,
        *,
        operational_alert_requested_event_name: str,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=QueueAccountErasureOperationalAlertJob.FUNCTION_ID,
            trigger=TriggerEvent(event=operational_alert_requested_event_name),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=QueueAccountErasureOperationalAlertJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('Mapping[str, object]', dict(context.event.data))
            payload = QueueAccountErasureOperationalAlertJob._parse_payload(data)
            step_input = {
                'erasure_id': payload.erasure_id,
                'module': payload.module,
                'failure_code': payload.failure_code,
                'closed_at': payload.closed_at,
                'due_at': payload.due_at,
                'incident_id': payload.incident_id,
            }

            async def queue_alert(values: dict[str, str]) -> None:
                alert_values = QueueAccountErasureOperationalAlertJob._values(values)
                await asyncio.to_thread(
                    use_case.execute,
                    alert_values,
                    UUID(values['incident_id']),
                )

            await context.step.run(
                'queue_account_erasure_operational_alert',
                queue_alert,
                step_input,
            )

        return _

    @staticmethod
    def _parse_payload(data: Mapping[str, object]) -> _Payload:
        try:
            return _Payload.model_validate(dict(data))
        except ValidationError as error:
            raise NonRetriableError(
                'Invalid account erasure operational alert payload'
            ) from error

    @staticmethod
    def _values(data: Mapping[str, str]) -> AccountErasureOperationalAlertValues:
        try:
            return AccountErasureOperationalAlertValues(
                erasure_id=UUID(data['erasure_id']),
                module=data['module'],
                failure_code=data['failure_code'],
                closed_at=datetime.fromisoformat(data['closed_at']),
                due_at=datetime.fromisoformat(data['due_at']),
            )
        except (KeyError, ValueError, InvalidCommunicationError) as error:
            raise NonRetriableError(
                'Invalid account erasure operational alert payload'
            ) from error
