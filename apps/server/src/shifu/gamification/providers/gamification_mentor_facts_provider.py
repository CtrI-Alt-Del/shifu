from sqlalchemy.exc import SQLAlchemyError

from shifu.gamification.core.domain.structures import GamificationOverview
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases.get_gamification_overview_use_case import (
    GetGamificationOverviewUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import AccountTimeZoneProvider, ClockProvider

_UNAVAILABLE = 'Os dados de Gamificação estão temporariamente indisponíveis.'


class GamificationMentorFactsProvider:
    """Read the learner's XP, level, streak and achievements for the Mentor.

    The facts come from the same overview the Gamification page shows, so the
    Mentor and the page never report different numbers. They are read-only: the
    Mentor never grants XP or changes a reward.
    """

    def __init__(
        self,
        database: GamificationDatabase,
        time_zones: AccountTimeZoneProvider,
        clock: ClockProvider,
    ) -> None:
        self._overview = GetGamificationOverviewUseCase(database)
        self._time_zones = time_zones
        self._clock = clock

    def read(self, account_id: str) -> tuple[tuple[str, str], ...]:
        try:
            overview = self._overview.execute(
                account_id,
                time_zone=self._time_zones.find_time_zone(account_id),
                now=self._clock.now(),
            )
        except SQLAlchemyError as error:
            raise ServiceUnavailableError(_UNAVAILABLE) from error
        return (
            ('level', str(overview.level)),
            ('xp', self._xp(overview)),
            ('streak', self._streak(overview)),
            ('achievements', self._achievements(overview)),
        )

    @staticmethod
    def _xp(overview: GamificationOverview) -> str:
        return (
            f'{overview.total_xp} no total; faltam {overview.xp_for_next_level} '
            f'para o nível {overview.level + 1}'
        )

    @staticmethod
    def _streak(overview: GamificationOverview) -> str:
        streak = overview.streak.streak
        if streak.current == 0:
            current = 'nenhum dia seguido no momento'
        elif streak.current == 1:
            current = '1 dia seguido'
        else:
            current = f'{streak.current} dias seguidos'
        return f'{current} (recorde: {streak.longest})' if streak.longest else current

    @staticmethod
    def _achievements(overview: GamificationOverview) -> str:
        summary = overview.achievements
        text = f'{summary.obtained_count} de {summary.catalog_count}'
        if not summary.recent:
            return text
        recent = ', '.join(achievement.name for achievement in summary.recent)
        return f'{text}; mais recentes: {recent}'
