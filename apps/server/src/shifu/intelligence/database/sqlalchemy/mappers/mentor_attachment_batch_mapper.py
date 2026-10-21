from shifu.intelligence.core.domain.entities import MentorAttachmentBatch
from shifu.intelligence.database.sqlalchemy.models import MentorAttachmentBatchModel


class MentorAttachmentBatchMapper:
    @staticmethod
    def to_entity(model: MentorAttachmentBatchModel) -> MentorAttachmentBatch:
        return MentorAttachmentBatch(
            id=model.id,
            account_id=model.account_id,
            session_id=model.session_id,
            generation=model.generation,
            expires_at=model.expires_at,
            consumed_by_message_id=model.consumed_by_message_id,
            revoked_at=model.revoked_at,
        )

    @staticmethod
    def to_model(batch: MentorAttachmentBatch) -> MentorAttachmentBatchModel:
        return MentorAttachmentBatchModel(
            id=batch.id,
            account_id=batch.account_id,
            session_id=batch.session_id,
            generation=batch.generation,
            expires_at=batch.expires_at,
            consumed_by_message_id=batch.consumed_by_message_id,
            revoked_at=batch.revoked_at,
        )
