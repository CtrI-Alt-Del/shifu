from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases import GetPracticeCalendarUseCase
from shifu.gamification.pipes import GamificationPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import AuthenticationPipe, SharedPipe


class CalendarDayResponse(BaseModel):
    day: date
    state: str


class StreakResponse(BaseModel):
    current: int
    longest: int


class Response(BaseModel):
    year: int
    month: int
    today: date
    days: tuple[CalendarDayResponse, ...]
    streak: StreakResponse
    earliest_practice_date: date | None = Field(
        serialization_alias='earliestPracticeDate'
    )


class GetPracticeCalendarController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/calendar',
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
            # No `ge`/`le`: the Spec contracts 400 via InvalidGamificationError
            # for an out-of-range month, and FastAPI's own bounds would answer
            # 422 before the use case's guard could run.
            year: Annotated[int, Query()],
            month: Annotated[int, Query()],
        ) -> Response:
            calendar = GetPracticeCalendarUseCase(database).execute(
                user.account_id,
                year,
                month,
                time_zone=user.time_zone,
                now=clock.now(),
            )
            return Response(
                year=calendar.year,
                month=calendar.month,
                today=calendar.today,
                days=tuple(
                    CalendarDayResponse(day=item.day, state=item.state.value)
                    for item in calendar.days
                ),
                streak=StreakResponse(
                    current=calendar.streak.current,
                    longest=calendar.streak.longest,
                ),
                earliest_practice_date=calendar.earliest_practice_date,
            )
