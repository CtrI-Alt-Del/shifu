from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import GetChoiceAttemptUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class NextActionResponse(BaseModel):
    competency_id: str
    activity_id: str
    difficulty: str
    type: str


class QuestionResultResponse(BaseModel):
    question_key: str
    prompt: str
    selected_option_keys: tuple[str, ...]
    score: Decimal
    is_correct: bool
    explanation: str
    disclosed_correct_option_keys: tuple[str, ...]


class Response(BaseModel):
    attempt_id: str
    activity_id: str
    status: str
    submitted_at: datetime
    retry_allowed: bool
    failure_message: str | None = None
    score: Decimal | None = None
    progress_before: Decimal | None = None
    progress_after: Decimal | None = None
    status_before: str | None = None
    status_after: str | None = None
    next_action: NextActionResponse | None = None
    questions: tuple[QuestionResultResponse, ...] = ()


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetChoiceAttemptController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
            '/activities/{activity_id}/attempts/{attempt_id}',
            response_model=Response,
            response_model_exclude_none=True,
            response_model_exclude_defaults=True,
            status_code=status.HTTP_200_OK,
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            competency_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            activity_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            attempt_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
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
        ) -> Response:
            detail = GetChoiceAttemptUseCase(
                database,
                provider,
                clock,
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                attempt_id,
            )
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
