from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, TypeAdapter

from shifu.gamification.core.domain.enums import CalendarDayState
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases import GetGamificationOverviewUseCase
from shifu.gamification.pipes import GamificationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import AuthenticationPipe, SharedPipe


class RecentAchievementResponse(BaseModel):
    achievement_id: str = Field(serialization_alias='achievementId')
    name: str
    criterion_label: str = Field(serialization_alias='criterionLabel')
    xp_reward: int = Field(serialization_alias='xpReward')
    achieved_at: datetime = Field(serialization_alias='achievedAt')


class AchievementsSummaryResponse(BaseModel):
    recent: tuple[RecentAchievementResponse, ...]
    obtained_count: int = Field(serialization_alias='obtainedCount')
    catalog_count: int = Field(serialization_alias='catalogCount')


class CalendarDayResponse(BaseModel):
    day: date
    state: CalendarDayState


class StreakResponse(BaseModel):
    current: int
    longest: int


class StreakOverviewResponse(BaseModel):
    streak: StreakResponse
    last_seven_days: tuple[CalendarDayResponse, ...] = Field(
        serialization_alias='lastSevenDays'
    )
    today: date
    is_today_pending: bool = Field(serialization_alias='isTodayPending')


class Response(BaseModel):
    level: int
    total_xp: int = Field(serialization_alias='totalXp')
    current_level_xp: int = Field(serialization_alias='currentLevelXp')
    next_level_xp: int = Field(serialization_alias='nextLevelXp')
    xp_for_next_level: int = Field(serialization_alias='xpForNextLevel')
    level_percentage: int = Field(serialization_alias='levelPercentage')
    streak: StreakOverviewResponse
    achievements: AchievementsSummaryResponse


_RESPONSE_ADAPTER = TypeAdapter[Response](Response)


class GetGamificationOverviewController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/overview',
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
            clock: Annotated[ClockProvider, Depends(SharedPipe.get_clock_provider)],
        ) -> Response:
            overview = GetGamificationOverviewUseCase(database).execute(
                user.account_id,
                time_zone=user.time_zone,
                now=clock.now(),
            )
            return _RESPONSE_ADAPTER.validate_python(overview, from_attributes=True)
