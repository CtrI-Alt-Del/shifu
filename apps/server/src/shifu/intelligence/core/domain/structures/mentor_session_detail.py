from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.structures.mentor_conversation_memory_item import (
    MentorConversationMemoryItem,
)
from shifu.intelligence.core.domain.structures.mentor_messages_page import (
    MentorMessagesPage,
)
from shifu.intelligence.core.domain.structures.mentor_response_snapshot import (
    MentorResponseSnapshot,
)
from shifu.intelligence.core.domain.structures.mentor_session_summary_state import (
    MentorSessionSummaryState,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorSessionDetail:
    session: MentorSession
    messages: MentorMessagesPage
    pending_learner_message_id: str | None
    response: MentorResponseSnapshot | None = None
    summary: MentorSessionSummaryState = MentorSessionSummaryState()
    memory_items: tuple[MentorConversationMemoryItem, ...] = ()
