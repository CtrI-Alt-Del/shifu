from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import DiscardPracticeDraftUseCase
from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.schemas.practice_draft_schemas import (
    PRACTICE_DRAFT_PATH,
    ActivityIdPath,
    CompetencyIdPath,
    GoalIdPath,
    SkillIdPath,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


class DiscardPracticeDraftController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.delete(
            PRACTICE_DRAFT_PATH,
            response_model=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )
        def _(
            goal_id: GoalIdPath,
            skill_id: SkillIdPath,
            competency_id: CompetencyIdPath,
            activity_id: ActivityIdPath,
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
            clock: Annotated[
                ClockProvider,
                Depends(LearningPipe.get_clock_provider),
            ],
        ) -> Response:
            DiscardPracticeDraftUseCase(database, provider, clock).execute(
                user.account_id, goal_id, skill_id, competency_id, activity_id
            )
            return Response(
                status_code=status.HTTP_204_NO_CONTENT,
                headers={'Cache-Control': 'private, no-store'},
            )
