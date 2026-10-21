from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures.mentor_response_block import (
    MentorResponseBlock,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorResponseSnapshot:
    attempt_id: str
    learner_message_id: str
    status: MentorResponseStatus
    blocks: tuple[MentorResponseBlock, ...]
    consultations: tuple[str, ...]
    last_sequence: int
    failure_code: str | None
    progress: MentorWorkflowStep | None = None
