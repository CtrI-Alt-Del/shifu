"""Erase Learning-owned records after an Identity account is closed."""

import asyncio
from collections.abc import Mapping
from typing import ClassVar, cast
from uuid import UUID

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent

from shifu.learning.core.use_cases import PurgeLearningDataForAccountUseCase
from shifu.shared.core.interfaces import (
    AccountErasureAcknowledgementProvider,
    AccountErasureTargetProvider,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)


class PurgeLearningDataOnAccountErasureJob:
    """Resolve the target in memory, then purge and acknowledge in one durable step."""

    FUNCTION_ID: ClassVar[str] = 'learning-purge-data-on-account-erasure'
    EVENT_NAME: ClassVar[str] = 'identity/account-erasure.requested'
    PARTICIPANT: ClassVar[str] = 'learning'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: PurgeLearningDataForAccountUseCase,
        *,
        target_provider: AccountErasureTargetProvider,
        acknowledgement_provider: AccountErasureAcknowledgementProvider,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=PurgeLearningDataOnAccountErasureJob.FUNCTION_ID,
            trigger=TriggerEvent(event=PurgeLearningDataOnAccountErasureJob.EVENT_NAME),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=PurgeLearningDataOnAccountErasureJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            erasure_id = PurgeLearningDataOnAccountErasureJob._parse_payload(data)

            async def purge_and_acknowledge(erasure_id: UUID) -> None:
                await PurgeLearningDataOnAccountErasureJob._purge_and_acknowledge(
                    erasure_id,
                    use_case,
                    target_provider,
                    acknowledgement_provider,
                )

            await context.step.run(
                'purge_learning_data',
                purge_and_acknowledge,
                erasure_id,
            )

        return _

    @staticmethod
    def _parse_payload(data: Mapping[str, object]) -> UUID:
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

    @staticmethod
    async def _purge_and_acknowledge(
        erasure_id: UUID,
        use_case: PurgeLearningDataForAccountUseCase,
        target_provider: AccountErasureTargetProvider,
        acknowledgement_provider: AccountErasureAcknowledgementProvider,
    ) -> None:
        account_id = await asyncio.to_thread(
            target_provider.resolve_account_id,
            erasure_id,
        )
        if account_id is None:
            return

        await asyncio.to_thread(use_case.execute, account_id)
        await asyncio.to_thread(
            acknowledgement_provider.acknowledge,
            erasure_id,
            PurgeLearningDataOnAccountErasureJob.PARTICIPANT,
        )
