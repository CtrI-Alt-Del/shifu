from __future__ import annotations

from typing import TYPE_CHECKING

from shifu.intelligence.core.domain.enums.learner_memory_change_kind import (
    LearnerMemoryChangeKind,
)
from shifu.shared.core.domain.entities import frozen_entity

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.enums.learner_memory_category import (
        LearnerMemoryCategory,
    )


@frozen_entity
class LearnerMemoryChange:
    """Immutable record of one memory creation or update, anchored to a message."""

    id: str
    account_id: str
    memory_id: str | None  # null after the memory is deleted
    session_id: str
    message_id: str
    kind: LearnerMemoryChangeKind
    category: LearnerMemoryCategory
    content: str | None  # erased with the memory
    previous_content: str | None
    created_at: datetime

    def __post_init__(self) -> None:
        if not all((self.id, self.account_id, self.session_id, self.message_id)):
            raise ValueError('Incomplete learner memory change')
        if self.memory_id is None and (
            self.content is not None or self.previous_content is not None
        ):
            raise ValueError('A change without a memory keeps no text')
        if (
            self.kind is LearnerMemoryChangeKind.CREATED
            and self.previous_content is not None
        ):
            raise ValueError('A created change has no previous content')
