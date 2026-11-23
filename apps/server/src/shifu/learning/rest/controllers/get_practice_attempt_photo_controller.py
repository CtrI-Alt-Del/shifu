from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response as FastApiResponse

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import GetPracticeAttemptPhotoUseCase
from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.schemas.practice_draft_schemas import (
    ID_PATTERN,
    ActivityIdPath,
    CompetencyIdPath,
    GoalIdPath,
    SkillIdPath,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import FileStorageProvider
from shifu.shared.pipes import AuthenticationPipe


class GetPracticeAttemptPhotoController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
            '/activities/{activity_id}/attempts/{attempt_id}'
            '/practice-photos/{photo_id}/content',
            response_model=None,
            response_class=FastApiResponse,
            status_code=200,
        )
        def _(
            goal_id: GoalIdPath,
            skill_id: SkillIdPath,
            competency_id: CompetencyIdPath,
            activity_id: ActivityIdPath,
            attempt_id: Annotated[str, Path(pattern=ID_PATTERN)],
            photo_id: Annotated[str, Path(pattern=ID_PATTERN)],
            user: Annotated[
                AuthenticatedUser,
                Depends(AuthenticationPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            storage: Annotated[
                FileStorageProvider,
                Depends(LearningPipe.get_practice_photo_storage_provider),
            ],
        ) -> FastApiResponse:
            photo = GetPracticeAttemptPhotoUseCase(database, storage).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                attempt_id,
                photo_id,
            )
            return FastApiResponse(
                content=photo.content,
                media_type=photo.media_type,
                headers={
                    'Cache-Control': 'private, no-store',
                    'X-Content-Type-Options': 'nosniff',
                    'Content-Length': str(len(photo.content)),
                },
            )
