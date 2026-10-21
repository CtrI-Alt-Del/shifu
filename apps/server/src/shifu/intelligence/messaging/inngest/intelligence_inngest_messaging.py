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


class IntelligenceInngestMessaging:
    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        purge_mentor_attachments_use_case: PurgeMentorAttachmentsUseCase,
        purge_mentor_summaries_use_case: PurgeMentorSummariesForAccountUseCase,
        account_deleted_event_name: str,
    ) -> list[Function[object]]:
        return [
            cast(
                'Function[object]',
                PurgeMentorAttachmentsOnAccountDeletedJob.handle(
                    inngest,
                    purge_mentor_attachments_use_case,
                    account_deleted_event_name=account_deleted_event_name,
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
