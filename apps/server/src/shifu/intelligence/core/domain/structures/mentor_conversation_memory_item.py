from datetime import datetime

from shifu.intelligence.core.domain.enums.learner_memory_category import (
    LearnerMemoryCategory,
)
from shifu.intelligence.core.domain.enums.learner_memory_change_kind import (
    LearnerMemoryChangeKind,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorConversationMemoryItem:
    change_id: str  # serialized as `id` by the REST response
    source_message_id: str
    kind: LearnerMemoryChangeKind
    category: LearnerMemoryCategory
    memory_id: str | None  # null after the memory is deleted
    content: str | None
    previous_content: str | None
    created_at: datetime
