from shifu.intelligence.core.domain.structures import (
    LearnerMemoryOrigin,
    LearnerMemoryOriginView,
)
from shifu.intelligence.database.sqlalchemy.models import LearnerMemoryOriginModel


class LearnerMemoryOriginMapper:
    @staticmethod
    def to_model(
        origin_id: str, memory_id: str, origin: LearnerMemoryOrigin
    ) -> LearnerMemoryOriginModel:
        return LearnerMemoryOriginModel(
            id=origin_id,
            memory_id=memory_id,
            session_id=origin.session_id,
            message_id=origin.message_id,
            declared_at=origin.declared_at,
        )

    @staticmethod
    def to_view(
        model: LearnerMemoryOriginModel, conversation_title: str | None
    ) -> LearnerMemoryOriginView:
        """An origin is available only while its conversation and message exist."""
        is_available = model.message_id is not None and conversation_title is not None
        return LearnerMemoryOriginView(
            session_id=model.session_id,
            message_id=model.message_id,
            conversation_title=conversation_title,
            is_available=is_available,
            declared_at=model.declared_at,
        )
