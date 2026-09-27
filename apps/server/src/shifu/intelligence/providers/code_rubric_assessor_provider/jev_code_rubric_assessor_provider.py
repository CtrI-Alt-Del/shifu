from typing import ClassVar, Literal

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError as TransportValidationError

from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures.code_rubric_assessment_input import (
    CodeRubricAssessmentInput,
)
from shifu.shared.core.domain.structures.code_rubric_decisions import (
    CodeConceptDecision,
    CodeCriterionDecision,
    CodeRubricDecisions,
    CodeRubricLevel,
)

_UNAVAILABLE_MESSAGE = 'Avaliação de código temporariamente indisponível.'


class _ChoiceQuestion(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    type: Literal['choice'] = 'choice'
    instructions: str
    criteria: dict[str, str]


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
    questions: dict[str, _ChoiceQuestion]
    state: _DecisionState


class _ChoiceAnswer(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True)

    type: Literal['choice']
    choice: str


class _DecisionsResponse(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True)

    answers: dict[str, _ChoiceAnswer]


def _validated_level(level: int) -> CodeRubricLevel:
    if level == 0:
        return 0
    if level == 25:
        return 25
    if level == 50:
        return 50
    if level == 75:
        return 75
    if level == 100:
        return 100
    raise ServiceUnavailableError(_UNAVAILABLE_MESSAGE)


class JevCodeRubricAssessorProvider:
    _TIMEOUT_SECONDS: ClassVar[float] = 30.0
    _UNAVAILABLE: ClassVar[str] = _UNAVAILABLE_MESSAGE

    def __init__(
        self,
        api_key: str | None,
        client: httpx.Client,
        decisions_url: str,
        model: Literal['typesafe/jev-1.13'],
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._decisions_url = decisions_url
        self._model: Literal['typesafe/jev-1.13'] = model

    def assess(self, request: CodeRubricAssessmentInput) -> CodeRubricDecisions:
        if not self._api_key:
            raise ServiceUnavailableError(self._UNAVAILABLE)

        questions: dict[str, _ChoiceQuestion] = {}
        options: dict[str, dict[str, CodeRubricLevel]] = {}
        for criterion in request.rubric_criteria:
            question_id = f'rubric:{criterion.key}'
            criteria = {
                comment.id: f'{criterion.name}: {comment.text}'
                for comment in criterion.fixed_comments
            }
            criteria[criterion.inconclusive_comment.id] = (
                criterion.inconclusive_comment.text
            )
            questions[question_id] = _ChoiceQuestion(
                instructions=criterion.description,
                criteria=criteria,
            )
            options[question_id] = {
                comment.id: _validated_level(comment.level)
                for comment in criterion.fixed_comments
            }
            options[question_id][criterion.inconclusive_comment.id] = 'inconclusive'

        for concept in request.concept_criteria:
            question_id = f'concept:{concept.concept_id}'
            criteria = {
                observation.id: (
                    f'{observation.evidence} '
                    f'Limite de interpretação: {observation.interpretation_limit}'
                )
                for observation in concept.level_observations
            }
            criteria[concept.inconclusive_observation.id] = (
                concept.inconclusive_observation.text
            )
            questions[question_id] = _ChoiceQuestion(
                instructions=concept.description,
                criteria=criteria,
            )
            options[question_id] = {
                observation.id: _validated_level(observation.level)
                for observation in concept.level_observations
            }
            options[question_id][concept.inconclusive_observation.id] = 'inconclusive'

        if len(questions) != len(request.rubric_criteria) + len(
            request.concept_criteria
        ):
            raise ServiceUnavailableError(self._UNAVAILABLE)

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
        try:
            response = self._client.post(
                self._decisions_url,
                headers={'Authorization': f'Bearer {self._api_key}'},
                json=payload.model_dump(),
                timeout=self._TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            result = _DecisionsResponse.model_validate(response.json())
        except (httpx.HTTPError, ValueError, TransportValidationError):
            raise ServiceUnavailableError(self._UNAVAILABLE) from None

        if set(result.answers) != set(options):
            raise ServiceUnavailableError(self._UNAVAILABLE)
        if any(
            answer.choice not in options[question_id]
            for question_id, answer in result.answers.items()
        ):
            raise ServiceUnavailableError(self._UNAVAILABLE)

        return CodeRubricDecisions(
            criterion_levels=tuple(
                CodeCriterionDecision(
                    key=criterion.key,
                    level=options[f'rubric:{criterion.key}'][
                        result.answers[f'rubric:{criterion.key}'].choice
                    ],
                )
                for criterion in request.rubric_criteria
            ),
            concept_levels=tuple(
                CodeConceptDecision(
                    concept_id=concept.concept_id,
                    level=options[f'concept:{concept.concept_id}'][
                        result.answers[f'concept:{concept.concept_id}'].choice
                    ],
                )
                for concept in request.concept_criteria
            ),
        )
