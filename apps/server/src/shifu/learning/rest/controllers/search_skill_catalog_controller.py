from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from shifu.learning.core.domain.structures import SkillCatalogRow
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import SearchSkillCatalogUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumCatalogReader
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


class SearchSkillCatalogController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/goals/{goal_id}/skills/catalog',
            response_model=Response,
            status_code=status.HTTP_200_OK,
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
            curriculum_catalog_reader: Annotated[
                CurriculumCatalogReader,
                Depends(LearningPipe.get_curriculum_catalog_reader),
            ],
            query: Annotated[str | None, Query()] = None,
            cursor: Annotated[str | None, Query()] = None,
            limit: Annotated[int, Query()] = 20,
        ) -> Response:
            rows, next_cursor = SearchSkillCatalogUseCase(
                learning_database=learning_database,
                curriculum_catalog_reader=curriculum_catalog_reader,
            ).execute(
                account_id=user.account_id,
                goal_id=goal_id,
                query=query,
                cursor=cursor,
                limit=limit,
            )

            return SearchSkillCatalogController._to_response(rows, next_cursor)

    @staticmethod
    def _to_response(rows: list[SkillCatalogRow], next_cursor: str | None) -> Response:
        return Response(
            items=[
                CatalogSkill(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    already_in_goal=row.already_in_goal,
                    skill_experience_id=row.skill_experience_id,
                    foundations=[
                        CatalogFoundation(
                            skill_id=foundation.skill_id,
                            name=foundation.name,
                            status=foundation.status,
                        )
                        for foundation in row.foundations
                    ],
                )
                for row in rows
            ],
            next_cursor=next_cursor,
        )
