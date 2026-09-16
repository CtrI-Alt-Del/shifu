from enum import StrEnum


class SkillExperienceStatus(StrEnum):
    NOT_STARTED = 'not-started'
    DIAGNOSING = 'diagnosing'
    LEARNING = 'learning'
    COMPLETED = 'completed'
