from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel
from starlette.responses import JSONResponse

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.domain.errors import CurriculumGapError
from shifu.learning.core.use_cases.start_skill_use_case import StartSkillUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class Response(BaseModel):
    status: Literal['diagnosing'] = 'diagnosing'


class StartSkillController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/skills/{skill_id}/start',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[LearningDatabase, Depends(LearningPipe.get_database)],
            curriculum: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
        ) -> Response | JSONResponse:
            try:
                StartSkillUseCase(database, curriculum, clock).execute(
                    user.account_id, goal_id, skill_id
                )
            except CurriculumGapError:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        'code': 'curriculum_gap',
                        'message': 'Este Skill ainda não está pronto para iniciar.',
                    },
                )
            return Response()
