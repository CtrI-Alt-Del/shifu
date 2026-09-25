from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, Field, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import (
    GetCompetencyDetailUseCase,
    GetMaterialDetailUseCase,
)
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class RecommendationResponse(BaseModel):
    competency_id: str = Field(serialization_alias='competencyId')
    activity_id: str = Field(serialization_alias='activityId')
    difficulty: str
    type: str


class AvailableResponse(BaseModel):
    availability: Literal['available'] = 'available'
    goal_id: str = Field(serialization_alias='goalId')
    skill_id: str = Field(serialization_alias='skillId')
    skill_name: str = Field(serialization_alias='skillName')
    competency_id: str = Field(serialization_alias='competencyId')
    competency_name: str = Field(serialization_alias='competencyName')
    material_id: str = Field(serialization_alias='materialId')
    material_title: str = Field(serialization_alias='materialTitle')
    content: str
    recommendation: RecommendationResponse | None


class UnavailableResponse(BaseModel):
    availability: Literal['unavailable'] = 'unavailable'
    goal_id: str = Field(serialization_alias='goalId')
    skill_id: str = Field(serialization_alias='skillId')
    skill_name: str = Field(serialization_alias='skillName')
    competency_id: str = Field(serialization_alias='competencyId')
    competency_name: str = Field(serialization_alias='competencyName')
    material_id: str = Field(serialization_alias='materialId')
    focus_competency_id: str | None = Field(serialization_alias='focusCompetencyId')
    focus_competency_name: str | None = Field(serialization_alias='focusCompetencyName')


type Response = Annotated[
    AvailableResponse | UnavailableResponse,
    Field(discriminator='availability'),
]


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetMaterialDetailController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}'
            '/materials/{material_id}',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            competency_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            material_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser,
                Depends(AuthenticationPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
            curriculum_content_provider: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
        ) -> Response:
            detail = GetMaterialDetailUseCase(
                GetCompetencyDetailUseCase(database, curriculum_content_provider),
                curriculum_content_provider,
            ).execute(
                user.account_id,
                goal_id,
                skill_id,
                competency_id,
                material_id,
            )
            return _RESPONSE_ADAPTER.validate_python(detail, from_attributes=True)
