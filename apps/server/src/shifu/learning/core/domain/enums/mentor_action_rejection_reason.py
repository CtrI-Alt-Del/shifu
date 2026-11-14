from enum import StrEnum


class MentorActionRejectionReason(StrEnum):
    GOAL_UNAVAILABLE = 'goal_unavailable'
    SKILL_UNAVAILABLE = 'skill_unavailable'
    EXPERIENCE_UNAVAILABLE = 'experience_unavailable'
