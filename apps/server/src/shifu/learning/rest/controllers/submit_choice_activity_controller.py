from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Path,
    Response as FastAPIResponse,
    status,
)
from pydantic import BaseModel, ConfigDict, TypeAdapter, model_validator

from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    ChoiceSubmissionOutcome,
    CodeAnswer,
    CodeSubmittedFile,
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


class SubmittedFileRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    path: str
    content: str


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    question_key: str
    kind: Literal['single_choice', 'multiple_selection', 'javascript_stdin'] | None = (
        None
    )
    selected_option_keys: tuple[str, ...] | None = None
    files: tuple[SubmittedFileRequest, ...] | None = None

    @model_validator(mode='after')
    def validate_answer_shape(self) -> 'AnswerRequest':
        if self.kind == 'javascript_stdin':
            if self.files is None or self.selected_option_keys is not None:
                raise ValueError('Code answers require files only')
        elif self.selected_option_keys is None or self.files is not None:
            raise ValueError('Choice answers require selected option keys only')
        return self


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    submission_key: UUID
    answers: tuple[AnswerRequest, ...]
    activity_revision: str | None = None


class Response(BaseModel):
    attempt_id: str
    status: Literal['pending']
    result_url: str
    is_diagnostic: bool = False


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
            diagnostic_run_id: Annotated[
                UUID | None,
                Header(alias='X-Diagnostic-Run-Id'),
            ] = None,
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
                        CodeAnswer(
                            question_key=answer.question_key,
                            files=tuple(
                                CodeSubmittedFile(path=item.path, content=item.content)
                                for item in (answer.files or ())
                            ),
                        )
                        if answer.kind == 'javascript_stdin'
                        else ChoiceAnswerSubmission(
                            question_key=answer.question_key,
                            selected_option_keys=answer.selected_option_keys or (),
                        )
                        for answer in request.answers
                    ),
                    request.activity_revision,
                    str(diagnostic_run_id) if diagnostic_run_id is not None else None,
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
                    f'/learning/goals/{goal_id}/skills/{skill_id}/diagnostic'
                    if outcome.is_diagnostic
                    else f'/learning/goals/{goal_id}/skills/{skill_id}'
                    f'/competencies/{competency_id}/activities/{activity_id}'
                    f'/attempts/{outcome.attempt.attempt_id}'
                ),
                is_diagnostic=outcome.is_diagnostic,
            )
