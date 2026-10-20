from enum import StrEnum


class MentorSummaryFailureCode(StrEnum):
    NLP_UNAVAILABLE = 'nlp_unavailable'
    INVALID_OUTPUT = 'invalid_output'
    EXHAUSTED = 'exhausted'
