from shifu.intelligence.core.domain.entities import MentorMessage
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.database.sqlalchemy.models import MentorMessageModel


class MentorMessageMapper:
    @staticmethod
    def to_domain(model: MentorMessageModel) -> MentorMessage:
        return MentorMessage(
            id=model.id,
            session_id=model.session_id,
            role=MentorMessageRole(model.role),
            content=model.content,
            created_at=model.created_at,
            in_reply_to_message_id=model.in_reply_to_message_id,
        )

    @staticmethod
    def to_model(message: MentorMessage) -> MentorMessageModel:
        return MentorMessageModel(
            id=message.id,
            session_id=message.session_id,
            role=message.role.value,
            content=message.content,
            created_at=message.created_at,
            in_reply_to_message_id=message.in_reply_to_message_id,
        )
