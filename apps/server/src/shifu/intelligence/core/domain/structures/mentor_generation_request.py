from shifu.intelligence.core.domain.entities.mentor_message import MentorMessage
from shifu.intelligence.core.domain.structures.mentor_attachment_context import (
    MentorAttachmentContext,
)
from shifu.intelligence.core.domain.structures.mentor_conversation_summary_context import (
    MentorConversationSummaryContext,
)
from shifu.intelligence.core.domain.structures.mentor_response_block import (
    MentorResponseBlock,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.mentor_context_snapshot import (
    MentorContextSnapshot,
)


@structure
class MentorGenerationRequest:
    session_id: str
    learner_message_id: str
    attempt_id: str
    requested_part: str
    history: tuple[MentorMessage, ...]  # only messages after the summary boundary
    context: MentorContextSnapshot
    approved_blocks: tuple[MentorResponseBlock, ...]
    correction: str | None
    attachment_context: MentorAttachmentContext | None = None
    summary: MentorConversationSummaryContext | None = None  # read by the reviewer only
