"""Purge all Intelligence-owned data for one pending account erasure."""

import asyncio
from collections.abc import Mapping
from typing import ClassVar, cast
from uuid import UUID

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent

from shifu.intelligence.core.use_cases import (
    PurgeAiQuotaForAccountUseCase,
    PurgeLearnerMemoriesForAccountUseCase,
    PurgeMentorActionProposalsForAccountUseCase,
    PurgeMentorAttachmentsUseCase,
    PurgeMentorSummariesForAccountUseCase,
    PurgePlanningSessionsForAccountUseCase,
)
from shifu.shared.core.interfaces import (
    AccountErasureAcknowledgementProvider,
    AccountErasureTargetProvider,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)


class PurgeIntelligenceOnAccountErasureJob:
    """Run all Intelligence purges before acknowledging the module once."""

    FUNCTION_ID: ClassVar[str] = 'intelligence-purge-account-data-on-account-erasure'

    @staticmethod
    def handle(
        inngest: Inngest,
        *,
        account_erasure_requested_event_name: str,
        account_erasure_target_provider: AccountErasureTargetProvider,
        account_erasure_acknowledgement_provider: (
            AccountErasureAcknowledgementProvider
        ),
        purge_mentor_attachments_use_case: PurgeMentorAttachmentsUseCase,
        purge_mentor_summaries_use_case: PurgeMentorSummariesForAccountUseCase,
        purge_learner_memories_use_case: PurgeLearnerMemoriesForAccountUseCase,
        purge_mentor_action_proposals_use_case: (
            PurgeMentorActionProposalsForAccountUseCase
        ),
        purge_ai_quota_use_case: PurgeAiQuotaForAccountUseCase,
        purge_planning_sessions_use_case: PurgePlanningSessionsForAccountUseCase,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=PurgeIntelligenceOnAccountErasureJob.FUNCTION_ID,
            trigger=TriggerEvent(event=account_erasure_requested_event_name),
            retries=3,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=PurgeIntelligenceOnAccountErasureJob.FUNCTION_ID,
            max_attempts=4,
        )
        async def _(context: Context) -> None:
            data = cast('Mapping[str, object]', dict(context.event.data))
            erasure_id = PurgeIntelligenceOnAccountErasureJob._parse_erasure_id(data)

            async def purge_mentor_attachments(erasure_id: UUID) -> bool:
                return await (
                    PurgeIntelligenceOnAccountErasureJob._purge_mentor_attachments(
                        account_erasure_target_provider,
                        purge_mentor_attachments_use_case,
                        erasure_id,
                    )
                )

            async def purge_mentor_summaries(erasure_id: UUID) -> bool:
                return await (
                    PurgeIntelligenceOnAccountErasureJob._purge_mentor_summaries(
                        account_erasure_target_provider,
                        purge_mentor_summaries_use_case,
                        erasure_id,
                    )
                )

            async def purge_learner_memories(erasure_id: UUID) -> bool:
                return await (
                    PurgeIntelligenceOnAccountErasureJob._purge_learner_memories(
                        account_erasure_target_provider,
                        purge_learner_memories_use_case,
                        erasure_id,
                    )
                )

            async def purge_mentor_action_proposals(erasure_id: UUID) -> bool:
                return await (
                    PurgeIntelligenceOnAccountErasureJob._purge_mentor_action_proposals(
                        account_erasure_target_provider,
                        purge_mentor_action_proposals_use_case,
                        erasure_id,
                    )
                )

            async def purge_ai_quota(erasure_id: UUID) -> bool:
                return await PurgeIntelligenceOnAccountErasureJob._purge_ai_quota(
                    account_erasure_target_provider,
                    purge_ai_quota_use_case,
                    erasure_id,
                )

            async def purge_planning_sessions(erasure_id: UUID) -> bool:
                return await (
                    PurgeIntelligenceOnAccountErasureJob._purge_planning_sessions(
                        account_erasure_target_provider,
                        purge_planning_sessions_use_case,
                        erasure_id,
                    )
                )

            async def acknowledge_intelligence(erasure_id: UUID) -> None:
                await PurgeIntelligenceOnAccountErasureJob._acknowledge(
                    account_erasure_acknowledgement_provider,
                    erasure_id,
                )

            results = (
                await context.step.run(
                    'purge_mentor_attachments',
                    purge_mentor_attachments,
                    erasure_id,
                ),
                await context.step.run(
                    'purge_mentor_summaries',
                    purge_mentor_summaries,
                    erasure_id,
                ),
                await context.step.run(
                    'purge_learner_memories',
                    purge_learner_memories,
                    erasure_id,
                ),
                await context.step.run(
                    'purge_mentor_action_proposals',
                    purge_mentor_action_proposals,
                    erasure_id,
                ),
                await context.step.run(
                    'purge_ai_quota',
                    purge_ai_quota,
                    erasure_id,
                ),
                await context.step.run(
                    'purge_planning_sessions',
                    purge_planning_sessions,
                    erasure_id,
                ),
            )
            if not all(results):
                return

            await context.step.run(
                'acknowledge_intelligence_purge',
                acknowledge_intelligence,
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
    async def _resolve_account_id(
        target_provider: AccountErasureTargetProvider,
        erasure_id: UUID,
    ) -> str | None:
        return await asyncio.to_thread(target_provider.resolve_account_id, erasure_id)

    @staticmethod
    async def _purge_mentor_attachments(
        target_provider: AccountErasureTargetProvider,
        use_case: PurgeMentorAttachmentsUseCase,
        erasure_id: UUID,
    ) -> bool:
        account_id = await PurgeIntelligenceOnAccountErasureJob._resolve_account_id(
            target_provider, erasure_id
        )
        if account_id is None:
            return False
        await asyncio.to_thread(use_case.execute_for_deleted_account, account_id)
        return True

    @staticmethod
    async def _purge_mentor_summaries(
        target_provider: AccountErasureTargetProvider,
        use_case: PurgeMentorSummariesForAccountUseCase,
        erasure_id: UUID,
    ) -> bool:
        account_id = await PurgeIntelligenceOnAccountErasureJob._resolve_account_id(
            target_provider, erasure_id
        )
        if account_id is None:
            return False
        await asyncio.to_thread(use_case.execute, account_id)
        return True

    @staticmethod
    async def _purge_learner_memories(
        target_provider: AccountErasureTargetProvider,
        use_case: PurgeLearnerMemoriesForAccountUseCase,
        erasure_id: UUID,
    ) -> bool:
        account_id = await PurgeIntelligenceOnAccountErasureJob._resolve_account_id(
            target_provider, erasure_id
        )
        if account_id is None:
            return False
        await asyncio.to_thread(use_case.execute, account_id)
        return True

    @staticmethod
    async def _purge_mentor_action_proposals(
        target_provider: AccountErasureTargetProvider,
        use_case: PurgeMentorActionProposalsForAccountUseCase,
        erasure_id: UUID,
    ) -> bool:
        account_id = await PurgeIntelligenceOnAccountErasureJob._resolve_account_id(
            target_provider, erasure_id
        )
        if account_id is None:
            return False
        await asyncio.to_thread(use_case.execute, account_id)
        return True

    @staticmethod
    async def _purge_ai_quota(
        target_provider: AccountErasureTargetProvider,
        use_case: PurgeAiQuotaForAccountUseCase,
        erasure_id: UUID,
    ) -> bool:
        account_id = await PurgeIntelligenceOnAccountErasureJob._resolve_account_id(
            target_provider, erasure_id
        )
        if account_id is None:
            return False
        await asyncio.to_thread(use_case.execute, account_id)
        return True

    @staticmethod
    async def _purge_planning_sessions(
        target_provider: AccountErasureTargetProvider,
        use_case: PurgePlanningSessionsForAccountUseCase,
        erasure_id: UUID,
    ) -> bool:
        account_id = await PurgeIntelligenceOnAccountErasureJob._resolve_account_id(
            target_provider, erasure_id
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
            'intelligence',
        )
