from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, Field

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.get_material_use_case import GetMaterialUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class Response(BaseModel):
    material_id: str = Field(serialization_alias='materialId')
    title: str
    material_type: str = Field(serialization_alias='materialType')
    content: str


class GetMaterialController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}/materials/{material_id}',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            competency_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            material_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[LearningDatabase, Depends(LearningPipe.get_database)],
            curriculum: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
        ) -> Response:
            material = GetMaterialUseCase(database, curriculum).execute(
                user.account_id, goal_id, skill_id, competency_id, material_id
            )
            return Response(
                material_id=material.id,
                title=material.title,
                material_type=material.material_type,
                content=material.content,
            )
