from dataclasses import field

from shifu.learning.core.domain.enums import ActivityAttemptKind, ActivityDifficulty
from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class ActivityEvaluatedPayload:
    account_id: str
    goal_id: str
    skill_experience_id: str
    skill_id: str
    competency_id: str
    activity_id: str
    attempt_id: str
    evaluation_id: str
    kind: ActivityAttemptKind
    difficulty: ActivityDifficulty
    score: str
    evaluated_at: str


@structure
class ActivityEvaluatedEvent(Event[ActivityEvaluatedPayload]):
    name: str = field(default='learning/activity-evaluated', init=False)
