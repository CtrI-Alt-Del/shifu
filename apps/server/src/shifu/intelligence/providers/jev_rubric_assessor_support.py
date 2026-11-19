"""Shared Jev Decisions-API plumbing for the code and translation rubric assessors.

Both assessors send the same closed-set "choice" decisions request shape and
apply the same validated-level/criterion/concept bookkeeping; only the
`_DecisionState` payload and the input/question types differ per assessor.
"""

from __future__ import annotations

from time import sleep
from typing import TYPE_CHECKING, ClassVar, Literal

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError as TransportValidationError

from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures.code_rubric_decisions import (
    CodeConceptDecision,
    CodeCriterionDecision,
    CodeRubricDecisions,
    CodeRubricLevel,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from shifu.shared.core.domain.structures.curriculum_code_concept_criterion_snapshot import (
        CurriculumCodeConceptCriterionSnapshot,
    )
    from shifu.shared.core.domain.structures.curriculum_code_rubric_criterion_snapshot import (
        CurriculumCodeRubricCriterionSnapshot,
    )
    from shifu.shared.core.domain.structures.curriculum_translation_rubric_criterion_snapshot import (
        CurriculumTranslationRubricCriterionSnapshot,
    )

    RubricCriterionLike = (
        CurriculumCodeRubricCriterionSnapshot
        | CurriculumTranslationRubricCriterionSnapshot
    )


class ChoiceQuestion(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    type: Literal['choice'] = 'choice'
    instructions: str
    criteria: dict[str, str]


class ChoiceAnswer(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True)

    type: Literal['choice']
    choice: str


class DecisionsResponse(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True)

    answers: dict[str, ChoiceAnswer]


def validated_level(level: int, unavailable_message: str) -> CodeRubricLevel:
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

    raise ServiceUnavailableError(unavailable_message)


def build_criteria_questions_and_options(
    rubric_criteria: Sequence[RubricCriterionLike],
    concept_criteria: Sequence[CurriculumCodeConceptCriterionSnapshot],
    unavailable_message: str,
) -> tuple[dict[str, ChoiceQuestion], dict[str, dict[str, CodeRubricLevel]]]:
    questions: dict[str, ChoiceQuestion] = {}
    options: dict[str, dict[str, CodeRubricLevel]] = {}
    for criterion in rubric_criteria:
        question_id = f'rubric:{criterion.key}'
        criteria = {
            comment.id: f'{criterion.name}: {comment.text}'
            for comment in criterion.fixed_comments
        }
        criteria[criterion.inconclusive_comment.id] = (
            criterion.inconclusive_comment.text
        )
        questions[question_id] = ChoiceQuestion(
            instructions=criterion.description,
            criteria=criteria,
        )
        options[question_id] = {
            comment.id: validated_level(comment.level, unavailable_message)
            for comment in criterion.fixed_comments
        }
        options[question_id][criterion.inconclusive_comment.id] = 'inconclusive'

    for concept in concept_criteria:
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
        questions[question_id] = ChoiceQuestion(
            instructions=concept.description,
            criteria=criteria,
        )
        options[question_id] = {
            observation.id: validated_level(observation.level, unavailable_message)
            for observation in concept.level_observations
        }
        options[question_id][concept.inconclusive_observation.id] = 'inconclusive'

    if len(questions) != len(rubric_criteria) + len(concept_criteria):
        raise ServiceUnavailableError(unavailable_message)
    return questions, options


def build_rubric_decisions(
    result: DecisionsResponse,
    options: dict[str, dict[str, CodeRubricLevel]],
    rubric_criteria: Sequence[RubricCriterionLike],
    concept_criteria: Sequence[CurriculumCodeConceptCriterionSnapshot],
    unavailable_message: str,
) -> CodeRubricDecisions:
    if set(result.answers) != set(options):
        raise ServiceUnavailableError(unavailable_message)

    if any(
        answer.choice not in options[question_id]
        for question_id, answer in result.answers.items()
    ):
        raise ServiceUnavailableError(unavailable_message)

    return CodeRubricDecisions(
        criterion_levels=tuple(
            CodeCriterionDecision(
                key=criterion.key,
                level=options[f'rubric:{criterion.key}'][
                    result.answers[f'rubric:{criterion.key}'].choice
                ],
            )
            for criterion in rubric_criteria
        ),
        concept_levels=tuple(
            CodeConceptDecision(
                concept_id=concept.concept_id,
                level=options[f'concept:{concept.concept_id}'][
                    result.answers[f'concept:{concept.concept_id}'].choice
                ],
            )
            for concept in concept_criteria
        ),
    )


class JevDecisionsClient:
    """Retrying HTTP transport for the Jev Decisions API, shared by every assessor."""

    _TIMEOUT_SECONDS: ClassVar[float] = 30.0
    _RETRY_DELAY_SECONDS: ClassVar[float] = 0.5
    _RETRYABLE_STATUS_CODES: ClassVar[frozenset[int]] = frozenset(
        {429, 500, 502, 503, 504}
    )

    def __init__(
        self,
        client: httpx.Client,
        decisions_url: str,
        api_key: str | None,
        unavailable_message: str,
    ) -> None:
        self._client = client
        self._decisions_url = decisions_url
        self._api_key = api_key
        self._unavailable = unavailable_message

    @property
    def api_key(self) -> str | None:
        return self._api_key

    def request_decisions(self, payload: BaseModel) -> DecisionsResponse:
        for attempt in range(2):
            try:
                response = self._client.post(
                    self._decisions_url,
                    headers={'Authorization': f'Bearer {self._api_key}'},
                    json=payload.model_dump(),
                    timeout=self._TIMEOUT_SECONDS,
                )
                if (
                    attempt == 0
                    and response.status_code in self._RETRYABLE_STATUS_CODES
                ):
                    sleep(self._RETRY_DELAY_SECONDS)
                    continue

                response.raise_for_status()
                return DecisionsResponse.model_validate(response.json())
            except httpx.TransportError:
                if attempt == 0:
                    sleep(self._RETRY_DELAY_SECONDS)
                    continue
            except (httpx.HTTPError, ValueError, TransportValidationError):
                pass
            raise ServiceUnavailableError(self._unavailable) from None
        raise ServiceUnavailableError(self._unavailable)
