from enum import StrEnum


class MentorWorkflowStep(StrEnum):
    SUMMARIZE_CONTEXT = 'summarize-context'
    WRITE_ANSWER = 'write-answer'
    REVIEW_ANSWER = 'review-answer'
