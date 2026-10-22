from typing import cast

from inngest import Function, Inngest

from shifu.intelligence.core.use_cases import (
    PurgeMentorAttachmentsUseCase,
    PurgeMentorSummariesForAccountUseCase,
)
from shifu.intelligence.messaging.inngest.jobs import (
    PurgeMentorAttachmentsOnAccountDeletedJob,
    PurgeMentorSummariesOnAccountDeletedJob,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider


class IntelligenceInngestMessaging:
    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        purge_mentor_attachments_use_case: PurgeMentorAttachmentsUseCase,
        purge_mentor_summaries_use_case: PurgeMentorSummariesForAccountUseCase,
        account_deleted_event_name: str,
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
                ),
            ),
        ]
