from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class SkillCompletedPayload:
    account_id: str
    goal_id: str
    skill_experience_id: str
    skill_id: str
    initial_progress: str
    final_progress: str
    completed_at: str


@structure
class SkillCompletedEvent(Event[SkillCompletedPayload]):
    name: str = field(default='learning/skill-completed', init=False)
