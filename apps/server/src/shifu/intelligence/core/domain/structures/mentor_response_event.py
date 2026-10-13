from datetime import datetime
from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorResponseEventKind,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures.mentor_response_block import (
    MentorResponseBlock,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorResponseEvent:
    session_id: str
    attempt_id: str
    sequence: int
    kind: MentorResponseEventKind
    status: MentorResponseStatus
    block: MentorResponseBlock | None
    consultation: str | None
    failure_code: str | None
    created_at: datetime
    progress: MentorWorkflowStep | None = None
