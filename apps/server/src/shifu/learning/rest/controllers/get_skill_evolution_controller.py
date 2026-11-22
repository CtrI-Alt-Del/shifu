from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, PlainSerializer, TypeAdapter

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import GetSkillEvolutionUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.pipes import SharedPipe


def _utc_instant(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace('+00:00', 'Z')


class SkillEvolutionPointResponse(BaseModel):
    occurred_at: Annotated[datetime, PlainSerializer(_utc_instant, return_type=str)] = (
        Field(serialization_alias='occurredAt')
    )
    result: float
    is_partial: bool = Field(serialization_alias='isPartial')
    is_baseline: bool = Field(serialization_alias='isBaseline')


class Response(BaseModel):
    skill_experience_id: str = Field(serialization_alias='skillExperienceId')
    points: list[SkillEvolutionPointResponse]


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetSkillEvolutionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/panorama/skill-experiences/{skill_experience_id}/evolution',
            response_model=Response,
            status_code=200,
        )
        def _(
            skill_experience_id: str,
            user: Annotated[
                AuthenticatedUser,
                Depends(SharedPipe.get_authenticated_user),
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
            evolution = GetSkillEvolutionUseCase(
                database, curriculum_content_provider
            ).execute(user.account_id, skill_experience_id)
            return _RESPONSE_ADAPTER.validate_python(evolution, from_attributes=True)
