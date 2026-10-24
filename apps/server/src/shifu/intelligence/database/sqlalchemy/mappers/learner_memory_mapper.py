import unicodedata

from shifu.intelligence.core.domain.entities import LearnerMemory
from shifu.intelligence.core.domain.enums import LearnerMemoryCategory
from shifu.intelligence.database.sqlalchemy.models import LearnerMemoryModel


class LearnerMemoryMapper:
    @staticmethod
    def to_entity(model: LearnerMemoryModel) -> LearnerMemory:
        return LearnerMemory(
            id=model.id,
            account_id=model.account_id,
            category=LearnerMemoryCategory(model.category),
            content=model.content,
            version=model.version,
            last_declared_at=model.last_declared_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(memory: LearnerMemory) -> LearnerMemoryModel:
        return LearnerMemoryModel(
            id=memory.id,
            account_id=memory.account_id,
            category=memory.category.value,
            content=memory.content,
            content_search=LearnerMemoryMapper.to_search_content(memory.content),
            version=memory.version,
            last_declared_at=memory.last_declared_at,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )

    @staticmethod
    def apply(model: LearnerMemoryModel, memory: LearnerMemory) -> None:
        """Copy the mutable state of ``memory`` onto ``model``."""
        model.content = memory.content
        model.content_search = LearnerMemoryMapper.to_search_content(memory.content)
        model.version = memory.version
        model.last_declared_at = memory.last_declared_at
        model.updated_at = memory.updated_at

    @staticmethod
    def to_search_content(content: str) -> str:
        """Casefold and strip accents, like ``MentorSessionMapper.to_search_title``."""
        decomposed = unicodedata.normalize('NFKD', content.casefold())
        return ''.join(char for char in decomposed if not unicodedata.combining(char))
