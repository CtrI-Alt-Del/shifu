from shifu.intelligence.core.domain.structures.mentor_action_proposal_draft import (
    MentorActionProposalDraft,
)
from shifu.intelligence.core.domain.structures.mentor_generation_request import (
    MentorGenerationRequest,
)
from shifu.intelligence.core.domain.structures.mentor_response_block import (
    MentorResponseBlock,
)
from shifu.shared.core.domain.structures import MentorContextSnapshot, structure


@structure
class PreparedMentorResponse:
    attempt_id: str
    execution_owner: str
    account_id: str
    session_id: str
    learner_message_id: str
    context: MentorContextSnapshot
    local_blocks: tuple[MentorResponseBlock, ...]
    attachment_request: MentorGenerationRequest | None
    generation_fallback: MentorResponseBlock | None = None
    action_proposal: MentorActionProposalDraft | None = None
