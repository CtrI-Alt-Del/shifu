from typing import Annotated

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import ListSkillExperiencesOfSkillUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import AuthenticationPipe


_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class SkillExperienceReferenceResponse(BaseModel):
    goal_id: str = Field(serialization_alias='goalId')
    goal_title: str = Field(serialization_alias='goalTitle')
    skill_experience_id: str = Field(serialization_alias='skillExperienceId')
    skill_id: str = Field(serialization_alias='skillId')
    status: str


class Response(BaseModel):
    experiences: tuple[SkillExperienceReferenceResponse, ...]


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class ListSkillExperiencesOfSkillController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/skills/{skill_id}/experiences',
            response_model=Response,
            status_code=200,
        )
        def _(
            skill_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser,
                Depends(AuthenticationPipe.get_authenticated_user),
            ],
            database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
            ],
        ) -> Response:
            experiences = ListSkillExperiencesOfSkillUseCase(database).execute(
                user.account_id,
                skill_id,
            )
            return _RESPONSE_ADAPTER.validate_python(
                {'experiences': experiences}, from_attributes=True
            )
