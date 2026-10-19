from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentNotFoundError,
    MentorAttachmentUnavailableError,
)
from shifu.intelligence.core.domain.structures import MentorAttachmentFile
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import (
    FileStorageProvider,
    IdentifierProvider,
    MentorAccessProvider,
)


class ReadMentorAttachmentFileUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        access_provider: MentorAccessProvider,
        storage_provider: FileStorageProvider,
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider
        self._access_provider = access_provider
        self._storage_provider = storage_provider

    def execute(
        self,
        account_id: str,
        session_id: str,
        attachment_id: str,
        *,
        preview: bool,
    ) -> MentorAttachmentFile:
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            attachment = repositories.mentor_attachments.find_by_id(attachment_id)
            if (
                session is None
                or attachment is None
                or attachment.account_id != account_id
                or attachment.session_id != session_id
                or attachment.message_id is None
                or attachment.status
                not in {MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL}
            ):
                raise MentorAttachmentNotFoundError
        if preview and not attachment.media_type.startswith('image/'):
            raise MentorAttachmentNotFoundError
        object_key = (
            attachment.preview_key or attachment.object_key
            if preview
            else attachment.object_key
        )
        grant = self._access_provider.authorize(
            account_id, self._identifier_provider.generate()
        )
        self._access_provider.assert_current(grant)
        original_generation = attachment.generation
        try:
            content = self._storage_provider.read(object_key)
        except Exception as error:
            raise MentorAttachmentUnavailableError from error
        self._access_provider.assert_current(grant)
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            current = repositories.mentor_attachments.find_by_id(
                attachment_id, for_update=True
            )
            if (
                session is None
                or current is None
                or current.generation != original_generation
                or current.status
                not in {MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL}
            ):
                raise MentorAttachmentNotFoundError
        return MentorAttachmentFile(
            filename=attachment.filename,
            media_type=attachment.media_type,
            content=content,
        )
