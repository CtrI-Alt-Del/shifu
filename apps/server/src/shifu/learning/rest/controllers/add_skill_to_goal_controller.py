from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from shifu.learning.core.domain.entities import SkillExperience
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import AddSkillToGoalUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumCatalogProvider,
    IdentifierProvider,
)
from shifu.shared.pipes import SharedPipe


class Request(BaseModel):
    skill_id: str
    foundation_skill_ids: list[str] = []


class CreatedSkillExperience(BaseModel):
    id: str
    skill_id: str = Field(serialization_alias='skillId')
    status: str


class Response(BaseModel):
    created: list[CreatedSkillExperience]


class AddSkillToGoalController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/skills',
            response_model=Response,
            status_code=status.HTTP_201_CREATED,
        )
        def _(
            goal_id: str,
            body: Request,
            user: Annotated[
                AuthenticatedUser,
                Depends(SharedPipe.get_authenticated_user),
            ],
            learning_database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            curriculum_catalog_provider: Annotated[
                CurriculumCatalogProvider,
                Depends(LearningPipe.get_curriculum_catalog_provider),
            ],
            identifier_provider: Annotated[
                IdentifierProvider,
                Depends(SharedPipe.get_identifier_provider),
            ],
            clock_provider: Annotated[
                ClockProvider,
                Depends(SharedPipe.get_clock_provider),
            ],
        ) -> Response:
            created_experiences = AddSkillToGoalUseCase(
                learning_database=learning_database,
                curriculum_catalog_provider=curriculum_catalog_provider,
                identifier_provider=identifier_provider,
                clock_provider=clock_provider,
            ).execute(
                account_id=user.account_id,
                goal_id=goal_id,
                skill_id=body.skill_id,
                foundation_skill_ids=body.foundation_skill_ids,
            )

            return AddSkillToGoalController._to_response(created_experiences)

    @staticmethod
    def _to_response(created_experiences: list[SkillExperience]) -> Response:
        return Response(
            created=[
                CreatedSkillExperience(
                    id=experience.id,
                    skill_id=experience.skill_id,
                    status=experience.status.value,
                )
                for experience in created_experiences
            ],
        )
