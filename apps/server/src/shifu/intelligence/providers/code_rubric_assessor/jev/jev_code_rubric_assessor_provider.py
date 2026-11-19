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
from shifu.shared.core.domain.structures.code_rubric_assessment_input import (
    CodeRubricAssessmentInput,
)
from shifu.shared.core.domain.structures.code_rubric_decisions import (
    CodeRubricDecisions,
)

_UNAVAILABLE_MESSAGE = 'Avaliação de código temporariamente indisponível.'


class _ProjectFile(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    path: str
    content: str


class _DecisionState(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    question_kind: str
    prompt: str
    project_files: tuple[_ProjectFile, ...]
    submitted_paths: tuple[str, ...]


class _DecisionsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    model: Literal['typesafe/jev-1.13'] = 'typesafe/jev-1.13'
    questions: dict[str, ChoiceQuestion]
    state: _DecisionState


class JevCodeRubricAssessorProvider:
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

    def assess(self, request: CodeRubricAssessmentInput) -> CodeRubricDecisions:
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
                prompt=request.prompt,
                project_files=tuple(
                    _ProjectFile(path=path, content=content)
                    for path, content in request.project_files
                ),
                submitted_paths=request.submitted_paths,
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
