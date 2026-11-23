from datetime import date

from shifu.shared.core.domain.structures import structure


@structure
class RecentMastery:
    skill_experience_id: str
    goal_id: str
    goal_title: str
    skill_id: str
    skill_name: str
    competency_id: str
    competency_name: str
    mastered_on: date  # local date of CompetencyProgress.mastered_at
