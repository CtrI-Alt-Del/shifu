"""Purge Communication-owned data for one pending account erasure."""

import asyncio
from collections.abc import Mapping
from typing import ClassVar, cast
from uuid import UUID

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent

from shifu.communication.core.use_cases import (
    PurgeCommunicationDataForAccountUseCase,
)
from shifu.shared.core.interfaces import (
    AccountErasureAcknowledgementProvider,
    AccountErasureTargetProvider,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)


class PurgeCommunicationOnAccountErasureJob:
    """Delete the module's records and acknowledge only after its transaction."""

    FUNCTION_ID: ClassVar[str] = 'communication-purge-data-on-account-erasure'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: PurgeCommunicationDataForAccountUseCase,
        *,
        account_erasure_requested_event_name: str,
        account_erasure_target_provider: AccountErasureTargetProvider,
        account_erasure_acknowledgement_provider: (
            AccountErasureAcknowledgementProvider
        ),
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=PurgeCommunicationOnAccountErasureJob.FUNCTION_ID,
            trigger=TriggerEvent(event=account_erasure_requested_event_name),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=PurgeCommunicationOnAccountErasureJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('Mapping[str, object]', dict(context.event.data))
            erasure_id = PurgeCommunicationOnAccountErasureJob._parse_erasure_id(data)

            async def purge_communication(erasure_id: UUID) -> bool:
                account_id = await asyncio.to_thread(
                    account_erasure_target_provider.resolve_account_id,
                    erasure_id,
                )
                if account_id is None:
                    return False
                await asyncio.to_thread(use_case.execute, account_id)
                return True

            async def acknowledge_communication(erasure_id: UUID) -> None:
                await asyncio.to_thread(
                    account_erasure_acknowledgement_provider.acknowledge,
                    erasure_id,
                    'communication',
                )

            purged = await context.step.run(
                'purge_communication_data',
                purge_communication,
                erasure_id,
            )
            if not purged:
                return
            await context.step.run(
                'acknowledge_communication_purge',
                acknowledge_communication,
                erasure_id,
            )

        return _

    @staticmethod
    def _parse_erasure_id(data: Mapping[str, object]) -> UUID:
        if set(data) != {'erasure_id'}:
            raise NonRetriableError('Invalid account erasure event payload')
        value = data['erasure_id']
        try:
            if isinstance(value, UUID):
                return value
            if isinstance(value, str):
                return UUID(value)
        except ValueError as error:
            raise NonRetriableError('Invalid account erasure event payload') from error
        raise NonRetriableError('Invalid account erasure event payload')
