from enum import StrEnum


class XpSource(StrEnum):
    ACTIVITY = 'activity'
    DIAGNOSIS = 'diagnosis'
    COMPETENCY_MASTERY = 'competency-mastery'
    SKILL_COMPLETION = 'skill-completion'
    ACHIEVEMENT = 'achievement'
