from typing import Annotated

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from shifu.learning.core.domain.enums import (
    MentorActionOperation,
    MentorActionOutcome,
    MentorActionRejectionReason,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import RemoveSkillExperienceFromMentorUseCase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.shared.pipes import SharedPipe

_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    confirmation_id: str = Field(pattern=_ULID_PATTERN)
    skill_experience_id: str = Field(pattern=_ULID_PATTERN)


class Response(BaseModel):
    confirmation_id: str = Field(serialization_alias='confirmationId')
    operation: MentorActionOperation
    outcome: MentorActionOutcome
    rejection_reason: MentorActionRejectionReason | None = Field(
        serialization_alias='rejectionReason'
    )
    goal_id: str = Field(serialization_alias='goalId')
    skill_id: str | None = Field(serialization_alias='skillId')
    skill_experience_id: str | None = Field(serialization_alias='skillExperienceId')


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class RemoveSkillExperienceFromMentorController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/goals/{goal_id}/mentor-skill-removals',
            response_model=Response,
            status_code=200,
        )
        def _(
            goal_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            body: Request,
            user: Annotated[
                AuthenticatedUser,
                Depends(SharedPipe.get_authenticated_user),
            ],
            learning_database: Annotated[
                LearningDatabase,
                Depends(LearningPipe.get_database),
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
            resolution = RemoveSkillExperienceFromMentorUseCase(
                learning_database=learning_database,
                identifier_provider=identifier_provider,
                clock_provider=clock_provider,
            ).execute(
                account_id=user.account_id,
                goal_id=goal_id,
                confirmation_id=body.confirmation_id,
                skill_experience_id=body.skill_experience_id,
            )

            return _RESPONSE_ADAPTER.validate_python(resolution, from_attributes=True)
