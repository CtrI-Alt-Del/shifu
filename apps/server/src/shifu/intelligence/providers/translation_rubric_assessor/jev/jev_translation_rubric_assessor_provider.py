from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict

from shifu.intelligence.providers.jev_rubric_assessor_support import (
    ChoiceQuestion,
    JevDecisionsClient,
    build_criteria_questions_and_options,
    build_rubric_decisions,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures.code_rubric_decisions import (
    CodeRubricDecisions,
)
from shifu.shared.core.domain.structures.translation_rubric_assessment_input import (
    TranslationRubricAssessmentInput,
)

_UNAVAILABLE_MESSAGE = 'Avaliação de tradução temporariamente indisponível.'


class _DecisionState(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    question_kind: str
    source_text: str
    source_language: str
    target_language: str
    reference_translations: tuple[str, ...]
    submitted_text: str


class _DecisionsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    model: Literal['typesafe/jev-1.13'] = 'typesafe/jev-1.13'
    questions: dict[str, ChoiceQuestion]
    state: _DecisionState


class JevTranslationRubricAssessorProvider:
    def __init__(
        self,
        api_key: str | None,
        client: httpx.Client,
        decisions_url: str,
        model: Literal['typesafe/jev-1.13'],
    ) -> None:
        self._decisions = JevDecisionsClient(
            client, decisions_url, api_key, _UNAVAILABLE_MESSAGE
        )
        self._model: Literal['typesafe/jev-1.13'] = model

    def assess(self, request: TranslationRubricAssessmentInput) -> CodeRubricDecisions:
        if not self._decisions.api_key:
            raise ServiceUnavailableError(_UNAVAILABLE_MESSAGE)

        questions, options = build_criteria_questions_and_options(
            request.rubric_criteria, request.concept_criteria, _UNAVAILABLE_MESSAGE
        )
        payload = _DecisionsRequest(
            model=self._model,
            questions=questions,
            state=_DecisionState(
                question_kind=request.question_kind,
                source_text=request.source_text,
                source_language=request.source_language,
                target_language=request.target_language,
                reference_translations=tuple(request.reference_translations),
                submitted_text=request.submitted_text,
            ),
        )
        result = self._decisions.request_decisions(payload)
        return build_rubric_decisions(
            result,
            options,
            request.rubric_criteria,
            request.concept_criteria,
            _UNAVAILABLE_MESSAGE,
        )
