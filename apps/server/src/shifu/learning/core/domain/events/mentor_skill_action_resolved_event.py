from dataclasses import field
from typing import ClassVar

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class MentorSkillActionResolvedPayload:
    account_id: str
    confirmation_id: str
    operation: str
    outcome: str
    rejection_reason: str | None
    goal_id: str
    skill_id: str | None
    skill_experience_id: str | None
    resolved_at: str


@structure
class MentorSkillActionResolvedEvent(Event[MentorSkillActionResolvedPayload]):
    EVENT_NAME: ClassVar[str] = 'learning/mentor-skill-action-resolved'
    name: str = field(default=EVENT_NAME, init=False)
