from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases import ListAchievementsUseCase
from shifu.gamification.pipes import GamificationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import AuthenticationPipe


class AchievementResponse(BaseModel):
    code: str
    family: str
    name: str
    description: str
    criterion_label: str = Field(serialization_alias='criterionLabel')
    xp_reward: int = Field(serialization_alias='xpReward')
    state: str
    unlocked_at: datetime | None = Field(serialization_alias='unlockedAt')
    progress_current: int | None = Field(serialization_alias='progressCurrent')
    progress_target: int | None = Field(serialization_alias='progressTarget')


class Response(BaseModel):
    level: int
    total_xp: int = Field(serialization_alias='totalXp')
    xp_for_next_level: int = Field(serialization_alias='xpForNextLevel')
    achievements: tuple[AchievementResponse, ...]


class ListAchievementsController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/achievements',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            user: Annotated[
                AuthenticatedUser, Depends(AuthenticationPipe.get_authenticated_user)
            ],
            database: Annotated[
                GamificationDatabase, Depends(GamificationPipe.get_database)
            ],
        ) -> Response:
            overview = ListAchievementsUseCase(database).execute(user.account_id)
            return Response(
                level=overview.level,
                total_xp=overview.total_xp,
                xp_for_next_level=overview.xp_for_next_level,
                achievements=tuple(
                    AchievementResponse(
                        code=achievement.code,
                        family=achievement.family.value,
                        name=achievement.name,
                        description=achievement.description,
                        criterion_label=achievement.criterion_label,
                        xp_reward=achievement.xp_reward,
                        state=achievement.state,
                        unlocked_at=achievement.unlocked_at,
                        progress_current=achievement.progress_current,
                        progress_target=achievement.progress_target,
                    )
                    for achievement in overview.achievements
                ),
            )
