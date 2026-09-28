from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, status
from pydantic import BaseModel, Field

from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import CompleteDiagnosticUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe

_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class Response(BaseModel):
    status: Literal['learning', 'completed']
    diagnostic_run_id: UUID = Field(serialization_alias='diagnosticRunId')


class CompleteDiagnosticController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/skills/{skill_id}/diagnostic/complete',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser,
                Depends(AuthenticationPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            curriculum: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
            clock: Annotated[ClockProvider, Depends(LearningPipe.get_clock_provider)],
            diagnostic_run_id: Annotated[
                UUID,
                Header(alias='X-Diagnostic-Run-Id'),
            ],
        ) -> Response:
            experience = CompleteDiagnosticUseCase(
                database,
                curriculum,
                clock,
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                str(diagnostic_run_id),
            )
            state = (
                'learning'
                if experience.status is SkillExperienceStatus.LEARNING
                else 'completed'
            )
            return Response(
                status=state,
                diagnostic_run_id=diagnostic_run_id,
            )
