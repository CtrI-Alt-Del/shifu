from datetime import date
from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class CompletedSkill:
    skill_experience_id: str
    goal_id: str
    goal_title: str
    skill_id: str
    skill_name: str
    final_result: Decimal | None  # SkillCompletionSummary.final_progress
    completed_on: date  # local date
