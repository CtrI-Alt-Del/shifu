from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class CompetencyMasteredPayload:
    account_id: str
    goal_id: str
    skill_experience_id: str
    skill_id: str
    competency_id: str
    progress: str
    mastered_at: str


@structure
class CompetencyMasteredEvent(Event[CompetencyMasteredPayload]):
    name: str = field(default='learning/competency-mastered', init=False)
