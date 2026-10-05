from enum import StrEnum


class AchievementCriterionKind(StrEnum):
    DIAGNOSTICS_COMPLETED = 'diagnostics_completed'
    COMPETENCIES_MASTERED = 'competencies_mastered'
    SKILLS_COMPLETED = 'skills_completed'
    LONGEST_STREAK = 'longest_streak'
    LEVEL = 'level'
