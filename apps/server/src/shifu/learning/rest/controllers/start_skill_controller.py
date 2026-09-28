from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.start_skill_use_case import StartSkillUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class Response(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal['diagnosing'] = 'diagnosing'
    diagnostic_run_id: UUID = Field(serialization_alias='diagnosticRunId')


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    entry_key: UUID


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
            request: Request,
        ) -> Response:
            StartSkillUseCase(database, curriculum, clock).execute(
                user.account_id, goal_id, skill_id, str(request.entry_key)
            )
            return Response(diagnostic_run_id=request.entry_key)
