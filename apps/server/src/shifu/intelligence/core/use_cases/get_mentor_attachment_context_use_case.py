from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentNotFoundError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentContext,
    MentorAttachmentSource,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import (
    IdentifierProvider,
    MentorAccessProvider,
)


class GetMentorAttachmentContextUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider
        self._access_provider = access_provider

    def execute(
        self,
        account_id: str,
        session_id: str,
        attachment_ids: tuple[str, ...],
        page_numbers: tuple[int, ...] = (),
    ) -> MentorAttachmentContext:
        if (
            not attachment_ids
            or len(attachment_ids) > 5
            or len(set(attachment_ids)) != len(attachment_ids)
            or any(page < 1 for page in page_numbers)
            or len(set(page_numbers)) != len(page_numbers)
        ):
            raise MentorAttachmentNotFoundError
        grant = self._access_provider.authorize(
            account_id, self._identifier_provider.generate()
        )
        self._access_provider.assert_current(grant)
        with self._database.transaction() as repositories:
            if repositories.mentor_sessions.find_by_id(account_id, session_id) is None:
                raise MentorSessionNotFoundError
            attachments = tuple(
                repositories.mentor_attachments.find_by_id(attachment_id)
                for attachment_id in attachment_ids
            )
            if any(
                attachment is None
                or attachment.account_id != account_id
                or attachment.session_id != session_id
                or attachment.message_id is None
                or attachment.status
                not in {MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL}
                for attachment in attachments
            ):
                raise MentorAttachmentNotFoundError
            chunks = repositories.mentor_attachment_chunks.find_many_eligible(
                account_id,
                session_id,
                attachment_ids,
                page_numbers,
            )
            current_generations = {
                attachment.id: attachment.generation
                for attachment in attachments
                if attachment is not None
            }
            eligible_chunks = tuple(
                chunk
                for chunk in chunks
                if current_generations.get(chunk.attachment_id) == chunk.generation
            )
            self._access_provider.assert_current(grant)
            return MentorAttachmentContext(
                chunks=eligible_chunks,
                sources=tuple(
                    MentorAttachmentSource(
                        attachment_id=chunk.attachment_id,
                        chunk_id=chunk.chunk_id,
                        page_number=chunk.page_number,
                        locator=chunk.locator,
                    )
                    for chunk in eligible_chunks
                ),
            )
