from typing import Annotated

from fastapi import APIRouter, Depends, Response as FastApiResponse
from pydantic import TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import GetPracticeDraftUseCase
from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.schemas.practice_draft_schemas import (
    PRACTICE_DRAFT_PATH,
    ActivityIdPath,
    CompetencyIdPath,
    GoalIdPath,
    PracticeDraftSchemas,
    SkillIdPath,
)
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


class Response(PracticeDraftSchemas.Draft):
    pass


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetPracticeDraftController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(PRACTICE_DRAFT_PATH, response_model=Response, status_code=200)
        def _(
            goal_id: GoalIdPath,
            skill_id: SkillIdPath,
            competency_id: CompetencyIdPath,
            activity_id: ActivityIdPath,
            http_response: FastApiResponse,
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
            view = GetPracticeDraftUseCase(database, provider).execute(
                user.account_id, goal_id, skill_id, competency_id, activity_id
            )
            http_response.headers['Cache-Control'] = 'private, no-store'
            return _RESPONSE_ADAPTER.validate_python(view, from_attributes=True)
