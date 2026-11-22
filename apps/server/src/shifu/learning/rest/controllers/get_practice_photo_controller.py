from typing import Annotated

from fastapi import APIRouter, Depends, Response as FastApiResponse

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import GetPracticePhotoUseCase
from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.schemas.practice_draft_schemas import (
    PRACTICE_DRAFT_PATH,
    ActivityIdPath,
    CompetencyIdPath,
    GoalIdPath,
    RecordKeyPath,
    SkillIdPath,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider, FileStorageProvider
from shifu.shared.pipes import AuthenticationPipe


class GetPracticePhotoController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            f'{PRACTICE_DRAFT_PATH}/photos/{{record_key}}/content',
            response_model=None,
            response_class=FastApiResponse,
            status_code=200,
        )
        def _(
            goal_id: GoalIdPath,
            skill_id: SkillIdPath,
            competency_id: CompetencyIdPath,
            activity_id: ActivityIdPath,
            record_key: RecordKeyPath,
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
            storage: Annotated[
                FileStorageProvider,
                Depends(LearningPipe.get_practice_photo_storage_provider),
            ],
        ) -> FastApiResponse:
            photo = GetPracticePhotoUseCase(database, provider, storage).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                activity_id,
                record_key,
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
