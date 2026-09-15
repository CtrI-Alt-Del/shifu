from datetime import datetime

from shifu.learning.core.domain.enums import ActivityAttemptKind
from shifu.learning.core.domain.structures import ActivityAnswer
from shifu.shared.core.domain.entities import entity


@entity
class ActivityAttempt:
    id: str
    skill_experience_id: str
    competency_id: str
    activity_id: str
    kind: ActivityAttemptKind
    answers: tuple[ActivityAnswer, ...]
    submitted_at: datetime
