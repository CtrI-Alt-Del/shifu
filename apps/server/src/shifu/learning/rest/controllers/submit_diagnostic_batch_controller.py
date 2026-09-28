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
from pydantic import BaseModel, ConfigDict, Field

from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    CodeAnswer,
    CodeSubmittedFile,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.submit_diagnostic_batch_use_case import (
    DiagnosticSubmissionItem,
    SubmitDiagnosticBatchUseCase,
)
from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.controllers.submit_choice_activity_controller import (
    AnswerRequest,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class ItemRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    competency_id: str = Field(pattern=_ULID_PATTERN)
    activity_id: str = Field(pattern=_ULID_PATTERN)
    activity_revision: str = Field(min_length=1)
    answers: tuple[AnswerRequest, ...]


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    submission_key: UUID
    items: tuple[ItemRequest, ...]


class Response(BaseModel):
    status: Literal['pending']
    replayed: bool


class SubmitDiagnosticBatchController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/skills/{skill_id}/diagnostic/submissions',
            response_model=Response,
            status_code=status.HTTP_201_CREATED,
        )
        def _(
            request: Request,
            response: FastAPIResponse,
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            diagnostic_run_id: Annotated[UUID, Header(alias='X-Diagnostic-Run-Id')],
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[LearningDatabase, Depends(LearningPipe.get_database)],
            curriculum: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
            identifiers: Annotated[
                IdentifierProvider, Depends(LearningPipe.get_identifier_provider)
            ],
        ) -> Response:
            outcome = SubmitDiagnosticBatchUseCase(
                database, curriculum, clock, identifiers
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                str(diagnostic_run_id),
                request.submission_key,
                tuple(
                    DiagnosticSubmissionItem(
                        competency_id=item.competency_id,
                        activity_id=item.activity_id,
                        activity_revision=item.activity_revision,
                        answers=tuple(
                            CodeAnswer(
                                question_key=answer.question_key,
                                files=tuple(
                                    CodeSubmittedFile(
                                        path=file.path, content=file.content
                                    )
                                    for file in (answer.files or ())
                                ),
                            )
                            if answer.kind == 'javascript_stdin'
                            else ChoiceAnswerSubmission(
                                question_key=answer.question_key,
                                selected_option_keys=answer.selected_option_keys or (),
                            )
                            for answer in item.answers
                        ),
                    )
                    for item in request.items
                ),
            )
            response.status_code = (
                status.HTTP_200_OK if outcome.replayed else status.HTTP_201_CREATED
            )
            return Response(status='pending', replayed=outcome.replayed)
