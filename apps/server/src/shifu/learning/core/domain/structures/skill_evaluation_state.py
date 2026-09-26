from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.shared.core.domain.structures import structure


@structure
class SkillEvaluationState:
    evaluation_id: str
    attempt_id: str
    activity_id: str
    competency_id: str
    status: ActivityEvaluationStatus

    def __post_init__(self) -> None:
        if self.status is ActivityEvaluationStatus.COMPLETED:
            raise ValueError('A completed evaluation does not hold the Skill.')
