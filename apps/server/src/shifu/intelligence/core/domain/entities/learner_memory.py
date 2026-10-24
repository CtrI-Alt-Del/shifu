from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from shifu.intelligence.core.domain.errors.learner_memory_conflict_error import (
    LearnerMemoryConflictError,
)
from shifu.intelligence.core.domain.errors.learner_memory_content_invalid_error import (
    LearnerMemoryContentInvalidError,
)
from shifu.shared.core.domain.entities import entity

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.enums.learner_memory_category import (
        LearnerMemoryCategory,
    )
    from shifu.intelligence.core.domain.structures.learner_memory_statement import (
        LearnerMemoryStatement,
    )


@entity
class LearnerMemory:
    """One explicit learner declaration kept privately by the Mentor."""

    MAX_CONTENT_CODE_POINTS: ClassVar[int] = 280

    id: str
    account_id: str
    category: LearnerMemoryCategory
    content: str
    version: int
    last_declared_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        statement: LearnerMemoryStatement,
        declared_at: datetime,
        now: datetime,
    ) -> LearnerMemory:
        return cls(
            id=id,
            account_id=account_id,
            category=statement.category,
            content=statement.content,
            version=1,
            last_declared_at=declared_at,
            created_at=now,
            updated_at=now,
        )

    def apply_declaration(
        self, content: str, declared_at: datetime, now: datetime
    ) -> bool:
        """Apply a newer declaration; return False when it is not newer."""
        if declared_at <= self.last_declared_at:
            return False
        self.content = self._validated(content)
        self.version += 1
        self.last_declared_at = declared_at
        self.updated_at = now
        return True

    def edit(self, content: str, expected_version: int, now: datetime) -> None:
        cleaned = self._validated(content)
        if expected_version != self.version:
            raise LearnerMemoryConflictError
        self.content = cleaned
        self.version += 1
        self.last_declared_at = now
        self.updated_at = now

    @classmethod
    def _validated(cls, content: str) -> str:
        cleaned = content.strip()
        if not 1 <= len(cleaned) <= cls.MAX_CONTENT_CODE_POINTS:
            raise LearnerMemoryContentInvalidError
        return cleaned
