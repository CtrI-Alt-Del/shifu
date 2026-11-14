from enum import StrEnum


class PlanningOperationStage(StrEnum):
    """Informative step of a running planning operation, reported by the workflow."""

    ANALYZING = 'analyzing'
    RETRIEVING = 'retrieving'
    INTERVIEWING = 'interviewing'
    COMPOSING = 'composing'
