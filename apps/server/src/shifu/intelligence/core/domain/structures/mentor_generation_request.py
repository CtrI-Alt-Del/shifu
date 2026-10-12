from shifu.shared.core.domain.structures.mentor_context_snapshot import (
    MentorContextSnapshot,
)
from shifu.intelligence.core.domain.entities.mentor_message import MentorMessage
from shifu.intelligence.core.domain.structures.mentor_response_block import (
    MentorResponseBlock,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorGenerationRequest:
    session_id: str
    learner_message_id: str
    attempt_id: str
    requested_part: str
    history: tuple[MentorMessage, ...]
    context: MentorContextSnapshot
    approved_blocks: tuple[MentorResponseBlock, ...]
    correction: str | None
