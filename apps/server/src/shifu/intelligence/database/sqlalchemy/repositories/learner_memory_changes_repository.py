from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import LearnerMemoryChange
from shifu.intelligence.core.domain.structures import MentorConversationMemoryItem
from shifu.intelligence.database.sqlalchemy.mappers import LearnerMemoryChangeMapper
from shifu.intelligence.database.sqlalchemy.models import LearnerMemoryChangeModel


class SqlalchemyLearnerMemoryChangesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, change: LearnerMemoryChange) -> None:
        self._session.add(LearnerMemoryChangeMapper.to_model(change))
        self._session.flush()

    def find_items_by_session(
        self, account_id: str, session_id: str
    ) -> tuple[MentorConversationMemoryItem, ...]:
        models = self._session.scalars(
            select(LearnerMemoryChangeModel)
            .where(
                LearnerMemoryChangeModel.account_id == account_id,
                LearnerMemoryChangeModel.session_id == session_id,
            )
            .order_by(LearnerMemoryChangeModel.created_at, LearnerMemoryChangeModel.id)
        )
        return tuple(LearnerMemoryChangeMapper.to_item(model) for model in models)

    def erase_by_memory_id(self, account_id: str, memory_id: str) -> None:
        self._session.execute(
            update(LearnerMemoryChangeModel)
            .where(
                LearnerMemoryChangeModel.account_id == account_id,
                LearnerMemoryChangeModel.memory_id == memory_id,
            )
            .values(content=None, previous_content=None, memory_id=None)
        )

    def remove_by_session_id(self, session_id: str) -> None:
        self._session.execute(
            delete(LearnerMemoryChangeModel).where(
                LearnerMemoryChangeModel.session_id == session_id
            )
        )

    def remove_by_account_id(self, account_id: str) -> int:
        removed = self._session.scalars(
            delete(LearnerMemoryChangeModel)
            .where(LearnerMemoryChangeModel.account_id == account_id)
            .returning(LearnerMemoryChangeModel.id)
        ).all()
        return len(removed)

    def remove_all(self) -> None:
        self._session.execute(delete(LearnerMemoryChangeModel))
