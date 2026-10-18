from datetime import datetime

from shifu.intelligence.core.domain.entities import MentorAttachment
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
    MentorAttachmentNotFoundError,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentExtraction,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases.mentor_attachment_helpers import (
    LockedMentorAttachmentScope,
    run_with_locked_mentor_attachment_scope,
)
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class CompleteMentorAttachmentUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider

    def execute(
        self,
        attachment_id: str,
        generation: int,
        execution_owner: str,
        extraction: MentorAttachmentExtraction,
    ) -> MentorAttachmentStatus:
        with self._database.transaction() as repositories:
            candidate = repositories.mentor_attachments.find_by_id(attachment_id)
            if candidate is None:
                raise MentorAttachmentNotFoundError
            account_id = candidate.account_id
            batch_id = candidate.batch_id
        grant = self._access_provider.authorize(account_id, attachment_id)
        self._access_provider.assert_current(grant)
        now = self._clock_provider.now()
        return run_with_locked_mentor_attachment_scope(
            self._database,
            account_id,
            batch_id,
            lambda repositories, scope: self._complete(
                repositories,
                scope,
                account_id,
                attachment_id,
                generation,
                execution_owner,
                extraction,
                grant,
                now,
            ),
            attachment_id,
        )

    def _complete(
        self,
        repositories: IntelligenceDatabaseRepositories,
        scope: LockedMentorAttachmentScope,
        account_id: str,
        attachment_id: str,
        generation: int,
        execution_owner: str,
        extraction: MentorAttachmentExtraction,
        grant: MentorAccessGrant,
        now: datetime,
    ) -> MentorAttachmentStatus:
        attachment = scope.attachment
        batch = scope.batch
        if attachment is None or attachment.account_id != account_id:
            raise MentorAttachmentNotFoundError
        if (
            attachment.generation != generation
            or attachment.status is not MentorAttachmentStatus.PROCESSING
            or attachment.execution_owner != execution_owner
            or attachment.claim_expires_at is None
            or attachment.claim_expires_at <= now
        ):
            return attachment.status
        if (
            batch is None
            or batch.account_id != account_id
            or batch.revoked_at is not None
            or batch.consumed_by_message_id is not None
            or batch.expires_at <= now
            or not scope.session_available
        ):
            attachment.revoke()
            repositories.mentor_attachments.update(attachment)
            repositories.mentor_attachment_chunks.remove_by_attachment_id(attachment_id)
            return attachment.status
        self._validate_extraction(attachment, extraction)
        usable = bool(extraction.chunks)
        if not usable:
            attachment.fail_extraction(extraction, 'unreadable_file')
            repositories.mentor_attachment_chunks.remove_by_attachment_id(attachment_id)
        else:
            partial = bool(
                extraction.illegible_pages
                or extraction.uninterpreted_pages
                or extraction.limitations
            )
            status = (
                MentorAttachmentStatus.PARTIAL
                if partial
                else MentorAttachmentStatus.READY
            )
            attachment.apply_extraction(extraction, status)
            repositories.mentor_attachment_chunks.remove_by_attachment_id(attachment_id)
            repositories.mentor_attachment_chunks.add_many(extraction.chunks)
        repositories.mentor_attachments.update(attachment)
        self._access_provider.assert_current(grant)
        return attachment.status

    @staticmethod
    def _validate_extraction(
        attachment: MentorAttachment, extraction: MentorAttachmentExtraction
    ) -> None:
        page_sets = (
            extraction.analyzed_pages,
            extraction.illegible_pages,
            extraction.uninterpreted_pages,
        )
        pages = tuple(page for group in page_sets for page in group)
        if len(pages) != len(set(pages)):
            raise MentorAttachmentInvalidError
        analyzed = set(extraction.analyzed_pages)
        for chunk in extraction.chunks:
            if (
                chunk.attachment_id != attachment.id
                or chunk.generation != attachment.generation
                or (chunk.page_number is not None and chunk.page_number not in analyzed)
                or (
                    attachment.media_type == 'application/pdf'
                    and chunk.page_number is None
                )
                or (
                    attachment.media_type.startswith('image/')
                    and chunk.page_number != 1
                )
            ):
                raise MentorAttachmentInvalidError
