from typing import cast

from inngest import Function, Inngest

from shifu.intelligence.core.use_cases import PurgeMentorAttachmentsUseCase
from shifu.intelligence.messaging.inngest.jobs import (
    PurgeMentorAttachmentsOnAccountDeletedJob,
)


class IntelligenceInngestMessaging:
    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        purge_mentor_attachments_use_case: PurgeMentorAttachmentsUseCase,
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
        ]
