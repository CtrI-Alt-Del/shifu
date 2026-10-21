from shifu.intelligence.core.domain.entities import MentorAttachment
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.database.sqlalchemy.models import MentorAttachmentModel


class MentorAttachmentMapper:
    @staticmethod
    def to_entity(model: MentorAttachmentModel) -> MentorAttachment:
        return MentorAttachment(
            id=model.id,
            account_id=model.account_id,
            batch_id=model.batch_id,
            session_id=model.session_id,
            message_id=model.message_id,
            generation=model.generation,
            upload_key=model.upload_key,
            filename=model.filename,
            media_type=model.media_type,
            size_bytes=model.size_bytes,
            checksum=model.checksum,
            object_key=model.object_key,
            preview_key=model.preview_key,
            status=MentorAttachmentStatus(model.status),
            failure_code=model.failure_code,
            created_at=model.created_at,
            execution_owner=model.execution_owner,
            claim_expires_at=model.claim_expires_at,
            analyzed_pages=tuple(model.analyzed_pages),
            illegible_pages=tuple(model.illegible_pages),
            uninterpreted_pages=tuple(model.uninterpreted_pages),
            upload_completed_at=model.upload_completed_at,
        )

    @staticmethod
    def to_model(attachment: MentorAttachment) -> MentorAttachmentModel:
        return MentorAttachmentModel(
            id=attachment.id,
            account_id=attachment.account_id,
            batch_id=attachment.batch_id,
            session_id=attachment.session_id,
            message_id=attachment.message_id,
            generation=attachment.generation,
            upload_key=attachment.upload_key,
            filename=attachment.filename,
            media_type=attachment.media_type,
            size_bytes=attachment.size_bytes,
            checksum=attachment.checksum,
            object_key=attachment.object_key,
            preview_key=attachment.preview_key,
            status=attachment.status.value,
            failure_code=attachment.failure_code,
            created_at=attachment.created_at,
            execution_owner=attachment.execution_owner,
            claim_expires_at=attachment.claim_expires_at,
            analyzed_pages=list(attachment.analyzed_pages),
            illegible_pages=list(attachment.illegible_pages),
            uninterpreted_pages=list(attachment.uninterpreted_pages),
            upload_completed_at=attachment.upload_completed_at,
        )
