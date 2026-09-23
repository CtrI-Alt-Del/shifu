from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import SearchSkillCatalogUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.interfaces import CurriculumCatalogReader
from shifu.curriculum.providers import CurriculumCatalogReaderProvider


class CatalogFoundation(BaseModel):
	skill_id: str
	name: str
	status: str


class CatalogSkill(BaseModel):
	id: str
	name: str
	description: str
	already_in_goal: bool
	skill_experience_id: str | None
	foundations: list[CatalogFoundation]


class Response(BaseModel):
	items: list[CatalogSkill]
	next_cursor: str | None


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
			query: Annotated[str | None, Query()] = None,
			cursor: Annotated[str | None, Query()] = None,
			limit: Annotated[int, Query()] = 20,
			request: Request = None,
			learning_database: Annotated[
				LearningDatabase,
				Depends(LearningPipe.get_database),
			] = None,
		) -> Response:
			curriculum_database = request.app.state.curriculum_database
			with curriculum_database.transaction() as repos:
				catalog_reader = CurriculumCatalogReaderProvider(
					skills_repository=repos.skills,
					skill_foundations_repository=repos.skill_foundations,
				)

				use_case = SearchSkillCatalogUseCase(
					learning_database=learning_database,
					curriculum_catalog_reader=catalog_reader,
				)
				rows, next_cursor = use_case.execute(
					goal_id=goal_id,
					query=query,
					cursor=cursor,
					limit=limit,
				)

			return SearchSkillCatalogController._to_response(rows, next_cursor)

	@staticmethod
	def _to_response(rows, next_cursor) -> Response:
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
							skill_id=f.skill_id,
							name=f.name,
							status=f.status,
						)
						for f in row.foundations
					],
				)
				for row in rows
			],
			next_cursor=next_cursor,
		)
