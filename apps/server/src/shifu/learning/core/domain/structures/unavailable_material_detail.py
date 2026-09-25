from typing import Literal

from shifu.learning.core.domain.enums import CompetencyAvailability
from shifu.shared.core.domain.structures import structure


@structure
class UnavailableMaterialDetail:
    goal_id: str
    skill_id: str
    skill_name: str
    competency_id: str
    competency_name: str
    material_id: str
    availability: Literal[CompetencyAvailability.UNAVAILABLE]
    focus_competency_id: str | None
    focus_competency_name: str | None
