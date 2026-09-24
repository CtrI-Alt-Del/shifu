from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from shifu.learning.core.use_cases.list_available_skills_use_case import (
    ListAvailableSkillsUseCase,
)
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.shared.pipes import AuthenticationPipe


_UNAVAILABLE_MESSAGE = 'Esta Habilidade ainda não possui conteúdo avaliável suficiente.'


class SkillResponse(BaseModel):
    id: str
    name: str
    available: bool
    unavailable_reason: str | None = Field(serialization_alias='unavailableReason')


class Response(BaseModel):
    skills: tuple[SkillResponse, ...]


class ListAvailableSkillsController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/available-skills', response_model=Response, status_code=status.HTTP_200_OK
        )
        def _(
            _user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            curriculum: Annotated[
                CurriculumContentProvider,
                Depends(LearningPipe.get_curriculum_content_provider),
            ],
        ) -> Response:
            skills = ListAvailableSkillsUseCase(curriculum).execute()
            return Response(
                skills=tuple(
                    SkillResponse(
                        id=item.id,
                        name=item.name,
                        available=item.v2_eligible,
                        unavailable_reason=None
                        if item.v2_eligible
                        else _UNAVAILABLE_MESSAGE,
                    )
                    for item in skills
                )
            )
