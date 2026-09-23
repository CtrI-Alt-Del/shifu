from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response as FastAPIResponse, status
from pydantic import BaseModel, ConfigDict, TypeAdapter

from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    ChoiceSubmissionOutcome,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import SubmitChoiceActivityUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    question_key: str
    selected_option_keys: tuple[str, ...]


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    submission_key: UUID
    answers: tuple[AnswerRequest, ...]


class Response(BaseModel):
    attempt_id: str
    status: Literal['pending']
    result_url: str


_OUTCOME_ADAPTER = TypeAdapter[ChoiceSubmissionOutcome](ChoiceSubmissionOutcome)


class SubmitChoiceActivityController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
            '/activities/{activity_id}/attempts',
            response_model=Response,
            status_code=status.HTTP_201_CREATED,
        )
        def _(
            request: Request,
            response: FastAPIResponse,
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            competency_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            activity_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser,
                Depends(AuthenticationPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            provider: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
            identifiers: Annotated[
                IdentifierProvider,
                Depends(LearningPipe.get_identifier_provider),
            ],
        ) -> Response:
            outcome = _OUTCOME_ADAPTER.validate_python(
                SubmitChoiceActivityUseCase(
                    database,
                    provider,
                    clock,
                    identifiers,
                ).execute(
                    user.account_id,
                    goal_id,
                    skill_id,
                    competency_id,
                    activity_id,
                    str(request.submission_key),
                    tuple(
                        ChoiceAnswerSubmission(
                            question_key=answer.question_key,
                            selected_option_keys=answer.selected_option_keys,
                        )
                        for answer in request.answers
                    ),
                ),
                from_attributes=True,
            )
            response.status_code = (
                status.HTTP_200_OK if outcome.replayed else status.HTTP_201_CREATED
            )
            return Response(
                attempt_id=outcome.attempt.attempt_id,
                status='pending',
                result_url=(
                    f'/learning/goals/{goal_id}/skills/{skill_id}'
                    f'/competencies/{competency_id}/activities/{activity_id}'
                    f'/attempts/{outcome.attempt.attempt_id}'
                ),
            )
