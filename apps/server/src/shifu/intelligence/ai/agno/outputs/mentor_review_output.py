from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from shifu.intelligence.ai.agno.outputs.mentor_review_criterion_output import (
    MentorReviewCriterionOutput,
)


class MentorReviewOutput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    request_adherence: MentorReviewCriterionOutput
    fact_fidelity: MentorReviewCriterionOutput
    cumulative_solution: MentorReviewCriterionOutput
    diagnostic_safety: MentorReviewCriterionOutput
    privacy_access: MentorReviewCriterionOutput
    official_action_claims: MentorReviewCriterionOutput
