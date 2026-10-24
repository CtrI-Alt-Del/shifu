from enum import StrEnum


class MentorActionOutcome(StrEnum):
    ADDED = 'added'
    ALREADY_PRESENT = 'already_present'
    REMOVED = 'removed'
    REJECTED = 'rejected'
