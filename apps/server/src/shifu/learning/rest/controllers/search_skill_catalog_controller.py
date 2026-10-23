from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import SearchSkillCatalogUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumCatalogProvider
from shifu.shared.pipes import SharedPipe


class CatalogFoundation(BaseModel):
    skill_id: str = Field(serialization_alias='skillId')
    name: str
    status: str


class CatalogSkill(BaseModel):
    id: str
    name: str
    description: str
    already_in_goal: bool = Field(serialization_alias='alreadyInGoal')
    skill_experience_id: str | None = Field(serialization_alias='skillExperienceId')
    foundations: list[CatalogFoundation]


class Response(BaseModel):
    items: list[CatalogSkill]
    next_cursor: str | None = Field(serialization_alias='nextCursor')


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class SearchSkillCatalogController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/catalog',
            response_model=Response,
            status_code=200,
        )
        def _(
            goal_id: str,
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
            query: Annotated[str | None, Query()] = None,
            cursor: Annotated[str | None, Query()] = None,
            limit: Annotated[int, Query()] = 20,
        ) -> Response:
            rows, next_cursor = SearchSkillCatalogUseCase(
                learning_database=learning_database,
                curriculum_catalog_provider=curriculum_catalog_provider,
            ).execute(
                account_id=user.account_id,
                goal_id=goal_id,
                query=query,
                cursor=cursor,
                limit=limit,
            )

            return _RESPONSE_ADAPTER.validate_python(
                {'items': rows, 'next_cursor': next_cursor}, from_attributes=True
            )
