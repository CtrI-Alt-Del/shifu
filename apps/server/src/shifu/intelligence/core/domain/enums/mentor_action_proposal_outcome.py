from enum import StrEnum


class MentorActionProposalOutcome(StrEnum):
    ADDED = 'added'
    ALREADY_PRESENT = 'already_present'
    REMOVED = 'removed'
