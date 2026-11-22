from collections.abc import Callable

from shifu.intelligence.ai.agno.agents import PracticePhotoAssessmentAgent
from shifu.intelligence.ai.agno.outputs import PracticePhotoAssessmentOutput
from shifu.intelligence.ai.data.mentor_inference_usage import inference_guard_scope
from shifu.intelligence.core.domain.structures import MentorInferenceUsage
from shifu.shared.core.domain.errors import ServiceUnavailableError, ValidationError
from shifu.shared.core.domain.structures import (
    PracticeCriterionDecision,
    PracticePhotoAssessmentInput,
    PracticePhotoDecisions,
    PracticeRecordDecision,
)

_UNAVAILABLE = 'Avaliação das fotos temporariamente indisponível.'


class VisionPracticePhotoAssessorProvider:
    """Implements the Shared assessor port with the vision agent.

    The adapter receives the bytes from Learning's workflow; it never reads the
    Learning bucket and keeps no copy of the photos.
    """

    def __init__(
        self,
        agent: PracticePhotoAssessmentAgent | None,
        usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
    ) -> None:
        self._agent = agent
        self._usage_recorder = usage_recorder

    def assess(self, request: PracticePhotoAssessmentInput) -> PracticePhotoDecisions:
        agent = self._agent
        if agent is None:
            raise ServiceUnavailableError(_UNAVAILABLE)

        def assert_ready() -> None:
            # Zero data retention and the prompt-logging gate live in `enabled`.
            if not agent.enabled():
                raise ServiceUnavailableError(_UNAVAILABLE)

        with inference_guard_scope(assert_ready):
            output = agent.assess(request, usage_recorder=self._usage_recorder)
        return self._decisions(output)

    @staticmethod
    def _decisions(output: PracticePhotoAssessmentOutput) -> PracticePhotoDecisions:
        try:
            return PracticePhotoDecisions(
                criteria=tuple(
                    PracticeCriterionDecision(
                        key=item.key, level=item.level, comment_key=item.comment_key
                    )
                    for item in output.criteria
                ),
                records=tuple(
                    PracticeRecordDecision(
                        record_key=item.record_key, sufficient=item.sufficient
                    )
                    for item in output.records
                ),
            )
        except ValidationError as error:
            raise ServiceUnavailableError(_UNAVAILABLE) from error
