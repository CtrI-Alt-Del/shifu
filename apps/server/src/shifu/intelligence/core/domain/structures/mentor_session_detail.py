from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.structures.mentor_messages_page import (
    MentorMessagesPage,
)
from shifu.intelligence.core.domain.structures.mentor_response_snapshot import (
    MentorResponseSnapshot,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorSessionDetail:
    session: MentorSession
    messages: MentorMessagesPage
    pending_learner_message_id: str | None
    response: MentorResponseSnapshot | None = None
