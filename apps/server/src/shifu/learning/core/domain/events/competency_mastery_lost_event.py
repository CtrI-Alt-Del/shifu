from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class CompetencyMasteryLostPayload:
    account_id: str
    goal_id: str
    skill_experience_id: str
    skill_id: str
    competency_id: str
    progress: str
    lost_at: str


@structure
class CompetencyMasteryLostEvent(Event[CompetencyMasteryLostPayload]):
    name: str = field(default='learning/competency-mastery-lost', init=False)
