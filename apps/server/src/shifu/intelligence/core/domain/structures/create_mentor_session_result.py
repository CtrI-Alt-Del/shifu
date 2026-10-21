from shifu.intelligence.core.domain.structures.mentor_session_detail import (
    MentorSessionDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class CreateMentorSessionResult:
    detail: MentorSessionDetail
    created: bool
