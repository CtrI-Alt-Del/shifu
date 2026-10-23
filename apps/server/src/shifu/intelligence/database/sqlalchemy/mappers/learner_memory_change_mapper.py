from shifu.intelligence.core.domain.entities import LearnerMemoryChange
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryCategory,
    LearnerMemoryChangeKind,
)
from shifu.intelligence.core.domain.structures import MentorConversationMemoryItem
from shifu.intelligence.database.sqlalchemy.models import LearnerMemoryChangeModel


class LearnerMemoryChangeMapper:
    @staticmethod
    def to_model(change: LearnerMemoryChange) -> LearnerMemoryChangeModel:
        return LearnerMemoryChangeModel(
            id=change.id,
            account_id=change.account_id,
            memory_id=change.memory_id,
            session_id=change.session_id,
            message_id=change.message_id,
            kind=change.kind.value,
            category=change.category.value,
            content=change.content,
            previous_content=change.previous_content,
            created_at=change.created_at,
        )

    @staticmethod
    def to_item(model: LearnerMemoryChangeModel) -> MentorConversationMemoryItem:
        return MentorConversationMemoryItem(
            change_id=model.id,
            source_message_id=model.message_id,
            kind=LearnerMemoryChangeKind(model.kind),
            category=LearnerMemoryCategory(model.category),
            memory_id=model.memory_id,
            content=model.content,
            previous_content=model.previous_content,
            created_at=model.created_at,
        )
