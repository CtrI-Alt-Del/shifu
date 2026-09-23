from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import GetChoiceActivityUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class OptionResponse(BaseModel):
    key: str
    text: str


class QuestionResponse(BaseModel):
    key: str
    kind: Literal['single_choice', 'multiple_selection']
    prompt: str
    options: tuple[OptionResponse, ...]


class Response(BaseModel):
    activity_id: str
    title: str
    difficulty: str
    questions: tuple[QuestionResponse, ...]
    can_submit: bool
    latest_attempt_id: str | None
    unresolved_attempt_id: str | None


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetChoiceActivityController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
            '/activities/{activity_id}',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
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
        ) -> Response:
            detail = GetChoiceActivityUseCase(database, provider).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
            )
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
