from typing import cast

from inngest import Function, Inngest

from shifu.intelligence.core.use_cases import (
    PurgeAiQuotaForAccountUseCase,
    PurgeLearnerMemoriesForAccountUseCase,
    PurgeMentorActionProposalsForAccountUseCase,
    PurgeMentorAttachmentsUseCase,
    PurgeMentorSummariesForAccountUseCase,
    RecordMentorActionOutcomeUseCase,
)
from shifu.intelligence.messaging.inngest.jobs import (
    PurgeAiQuotaOnAccountDeletedJob,
    PurgeLearnerMemoriesOnAccountDeletedJob,
    PurgeMentorActionProposalsOnAccountDeletedJob,
    PurgeMentorAttachmentsOnAccountDeletedJob,
    PurgeMentorSummariesOnAccountDeletedJob,
    RecordMentorActionOutcomeJob,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider


class IntelligenceInngestMessaging:
    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        purge_mentor_attachments_use_case: PurgeMentorAttachmentsUseCase,
        purge_mentor_summaries_use_case: PurgeMentorSummariesForAccountUseCase,
        purge_learner_memories_use_case: PurgeLearnerMemoriesForAccountUseCase,
        purge_mentor_action_proposals_use_case: PurgeMentorActionProposalsForAccountUseCase,
        record_mentor_action_outcome_use_case: RecordMentorActionOutcomeUseCase,
        purge_ai_quota_use_case: PurgeAiQuotaForAccountUseCase,
        account_deleted_event_name: str,
        mentor_action_resolved_event_name: str,
        telemetry_provider: TelemetryProvider,
    ) -> list[Function[object]]:
        return [
            cast(
                'Function[object]',
                PurgeMentorAttachmentsOnAccountDeletedJob.handle(
                    inngest,
                    purge_mentor_attachments_use_case,
                    account_deleted_event_name=account_deleted_event_name,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                PurgeMentorSummariesOnAccountDeletedJob.handle(
                    inngest,
                    purge_mentor_summaries_use_case,
                    account_deleted_event_name=account_deleted_event_name,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                PurgeLearnerMemoriesOnAccountDeletedJob.handle(
                    inngest,
                    purge_learner_memories_use_case,
                    account_deleted_event_name=account_deleted_event_name,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                PurgeMentorActionProposalsOnAccountDeletedJob.handle(
                    inngest,
                    purge_mentor_action_proposals_use_case,
                    account_deleted_event_name=account_deleted_event_name,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                PurgeAiQuotaOnAccountDeletedJob.handle(
                    inngest,
                    purge_ai_quota_use_case,
                    account_deleted_event_name=account_deleted_event_name,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                RecordMentorActionOutcomeJob.handle(
                    inngest,
                    record_mentor_action_outcome_use_case,
                    outcome_event_name=mentor_action_resolved_event_name,
                    telemetry_provider=telemetry_provider,
                ),
            ),
        ]
