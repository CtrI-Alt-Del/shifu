from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.interfaces import IntelligenceDatabase


class ReleaseMentorAttachmentClaimUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database = database

    def execute(
        self, attachment_id: str, generation: int, execution_owner: str
    ) -> None:
        with self._database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(
                attachment_id, for_update=True
            )
            if (
                attachment is None
                or attachment.generation != generation
                or attachment.status is not MentorAttachmentStatus.PROCESSING
                or attachment.execution_owner != execution_owner
            ):
                return
            attachment.release_claim(execution_owner)
            repositories.mentor_attachments.update(attachment)
