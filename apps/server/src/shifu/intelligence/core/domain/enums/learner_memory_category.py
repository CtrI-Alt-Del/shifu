from enum import StrEnum


class LearnerMemoryCategory(StrEnum):
    EXPLANATION_PREFERENCE = 'explanation_preference'
    DECLARED_KNOWLEDGE = 'declared_knowledge'
    INTEREST_OR_INTENTION = 'interest_or_intention'
    RECURRING_DIFFICULTY = 'recurring_difficulty'
