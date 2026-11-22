"""Gamification consumer for Identity's opaque account-erasure event."""

import asyncio
from collections.abc import Mapping
from typing import ClassVar, cast
from uuid import UUID

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent

from shifu.gamification.core.use_cases import DeleteGamificationProfileUseCase
from shifu.shared.core.interfaces import (
    AccountErasureAcknowledgementProvider,
    AccountErasureTargetProvider,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)


class PurgeProfileOnAccountErasureJob:
    """Purge Gamification rows and acknowledge this participant once complete."""

    FUNCTION_ID: ClassVar[str] = 'gamification-purge-profile-on-account-erasure'

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: DeleteGamificationProfileUseCase,
        *,
        account_erasure_requested_event_name: str,
        account_erasure_target_provider: AccountErasureTargetProvider,
        account_erasure_acknowledgement_provider: AccountErasureAcknowledgementProvider,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=PurgeProfileOnAccountErasureJob.FUNCTION_ID,
            trigger=TriggerEvent(event=account_erasure_requested_event_name),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=PurgeProfileOnAccountErasureJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('Mapping[str, object]', dict(context.event.data))
            erasure_id = PurgeProfileOnAccountErasureJob._parse_erasure_id(data)

            async def purge_profile(erasure_id: UUID) -> bool:
                return await PurgeProfileOnAccountErasureJob._purge_profile(
                    account_erasure_target_provider,
                    use_case,
                    erasure_id,
                )

            async def acknowledge_gamification(erasure_id: UUID) -> None:
                await PurgeProfileOnAccountErasureJob._acknowledge(
                    account_erasure_acknowledgement_provider,
                    erasure_id,
                )

            purged = await context.step.run(
                'purge_gamification_profile',
                purge_profile,
                erasure_id,
            )
            if not purged:
                return
            await context.step.run(
                'acknowledge_gamification_purge',
                acknowledge_gamification,
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

    @staticmethod
    async def _purge_profile(
        target_provider: AccountErasureTargetProvider,
        use_case: DeleteGamificationProfileUseCase,
        erasure_id: UUID,
    ) -> bool:
        account_id = await asyncio.to_thread(
            target_provider.resolve_account_id,
            erasure_id,
        )
        if account_id is None:
            return False
        await asyncio.to_thread(use_case.execute, account_id)
        return True

    @staticmethod
    async def _acknowledge(
        acknowledgement_provider: AccountErasureAcknowledgementProvider,
        erasure_id: UUID,
    ) -> None:
        await asyncio.to_thread(
            acknowledgement_provider.acknowledge,
            erasure_id,
            'gamification',
        )
