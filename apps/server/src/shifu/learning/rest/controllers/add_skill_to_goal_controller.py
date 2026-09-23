from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import AddSkillToGoalUseCase
from shifu.learning.pipes import LearningPipe
from shifu.curriculum.providers import CurriculumCatalogReaderProvider
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.pipes import SharedPipe


class CreateExperienceItem(BaseModel):
	id: str
	skill_id: str
	status: str


class Response(BaseModel):
	created: list[CreateExperienceItem]


class Request_Body(BaseModel):
	skill_id: str
	foundation_skill_ids: list[str] = []


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
			body: Request_Body,
			request: Request = None,
			learning_database: Annotated[
				LearningDatabase,
				Depends(LearningPipe.get_database),
			] = None,
			identifier_provider: Annotated[
				IdentifierProvider,
				Depends(SharedPipe.get_identifier_provider),
			] = None,
		) -> Response:
			curriculum_database = request.app.state.curriculum_database
			with curriculum_database.transaction() as repos:
				catalog_reader = CurriculumCatalogReaderProvider(
					skills_repository=repos.skills,
					skill_foundations_repository=repos.skill_foundations,
				)

				use_case = AddSkillToGoalUseCase(
					learning_database=learning_database,
					curriculum_catalog_reader=catalog_reader,
					identifier_provider=identifier_provider,
				)
				created_experiences = use_case.execute(
					goal_id=goal_id,
					skill_id=body.skill_id,
					foundation_skill_ids=body.foundation_skill_ids,
				)

			return AddSkillToGoalController._to_response(created_experiences)

	@staticmethod
	def _to_response(created_experiences) -> Response:
		return Response(
			created=[
				CreateExperienceItem(
					id=exp.id,
					skill_id=exp.skill_id,
					status=exp.status,
				)
				for exp in created_experiences
			],
		)
