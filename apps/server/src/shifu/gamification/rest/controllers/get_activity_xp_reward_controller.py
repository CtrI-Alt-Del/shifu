from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, Field

from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases import GetActivityXpRewardUseCase
from shifu.gamification.pipes import GamificationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import AuthenticationPipe

_ULID_PATTERN = r'^[0-9A-Z]{26}$'


class Response(BaseModel):
    activity_id: str = Field(serialization_alias='activityId')
    attempt_id: str = Field(serialization_alias='attemptId')
    state: str
    additional_xp: int = Field(serialization_alias='additionalXp')
    granted_xp: int = Field(serialization_alias='grantedXp')
    maximum_xp: int | None = Field(serialization_alias='maximumXp')


class GetActivityXpRewardController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/activities/{activity_id}/attempts/{attempt_id}/xp-reward',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            activity_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            attempt_id: Annotated[str, Path(pattern=_ULID_PATTERN)],
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[
                GamificationDatabase, Depends(GamificationPipe.get_database)
            ],
        ) -> Response:
            reward = GetActivityXpRewardUseCase(database).execute(
                user.account_id, activity_id, attempt_id
            )
            return Response(
                activity_id=reward.activity_id,
                attempt_id=reward.attempt_id,
                state=reward.state.value,
                additional_xp=reward.additional_xp,
                granted_xp=reward.granted_xp,
                maximum_xp=reward.maximum_xp,
            )
