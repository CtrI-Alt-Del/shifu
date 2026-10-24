from enum import StrEnum


class MentorActionProposalStatus(StrEnum):
    PENDING = 'pending'
    DECLINED = 'declined'
    COMPLETED = 'completed'
    REJECTED = 'rejected'
