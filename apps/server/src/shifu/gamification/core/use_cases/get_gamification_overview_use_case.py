from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from shifu.gamification.core.domain.achievement_catalog import ACHIEVEMENT_CATALOG
from shifu.gamification.core.domain.achievement_criterion_label import (
    achievement_criterion_label,
)
from shifu.gamification.core.domain.current_practice_run import current_practice_run
from shifu.gamification.core.domain.derived_practice_streak import (
    derived_practice_streak,
)
from shifu.gamification.core.domain.entities import EarnedAchievement
from shifu.gamification.core.domain.entities.gamification_profile import (
    GamificationProfile,
)
from shifu.gamification.core.domain.practice_day_state import practice_day_state
from shifu.gamification.core.domain.resolved_time_zone import resolved_time_zone
from shifu.gamification.core.domain.structures import (
    AchievementsSummary,
    CalendarDay,
    GamificationOverview,
    PracticeStreak,
    RecentAchievement,
    StreakOverview,
)
from shifu.gamification.core.interfaces import GamificationDatabase

_WINDOW_DAYS = 7
_RECENT_LIMIT = 3


class GetGamificationOverviewUseCase:
    """Aggregate the account's level, constância and achievements into one read.

    The three reads share one transaction so the level, the streak and the
    achievement summary describe one consistent snapshot even while an XP
    cascade commits concurrently. Every derivation is either a stored value or
    one of the shared `core/domain` functions the practice calendar also uses,
    so the two surfaces cannot report different streaks for the same instant.
    """

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(
        self, account_id: str, *, time_zone: str | None, now: datetime
    ) -> GamificationOverview:
        today = now.astimezone(ZoneInfo(resolved_time_zone(time_zone))).date()

        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            dates = repositories.practice_days.find_many_dates_by_account_id(account_id)
            earned = repositories.earned_achievements.find_many_by_account_id(
                account_id
            )

        # An account whose profile row has not been created yet reads the
        # initial state rather than an error: this tab is the area's landing
        # surface and JN-01 describes that state as normal.
        level = profile.level if profile is not None else 1
        total_xp = profile.total_xp if profile is not None else 0
        stored_streak = profile.streak if profile is not None else PracticeStreak()

        current_level_xp = GamificationProfile.minimum_xp_for_level(level)
        next_level_xp = GamificationProfile.minimum_xp_for_level(level + 1)

        return GamificationOverview(
            level=level,
            total_xp=total_xp,
            current_level_xp=current_level_xp,
            next_level_xp=next_level_xp,
            xp_for_next_level=next_level_xp - total_xp,
            level_percentage=self._percentage(
                total_xp, current_level_xp=current_level_xp, next_level_xp=next_level_xp
            ),
            streak=self._streak_for(stored_streak, dates, today=today),
            achievements=self._achievements_for(earned),
        )

    @staticmethod
    def _percentage(total_xp: int, *, current_level_xp: int, next_level_xp: int) -> int:
        # The profile invariant keeps `total_xp` below `next_level_xp`, so the
        # ratio can never reach 100 and needs no upper clamp. The lower clamp
        # is live: a level preserved above a raised curve puts `total_xp` below
        # its own level's minimum, which would otherwise report a negative.
        return max(
            0,
            ((total_xp - current_level_xp) * 100) // (next_level_xp - current_level_xp),
        )

    @staticmethod
    def _streak_for(
        stored: PracticeStreak, dates: tuple[date, ...], *, today: date
    ) -> StreakOverview:
        ordered = tuple(sorted(set(dates)))
        earliest = ordered[0] if ordered else None
        practiced = frozenset(ordered)
        run = current_practice_run(ordered, today=today)
        run_dates = frozenset(run)

        window = tuple(
            today - timedelta(days=offset) for offset in reversed(range(_WINDOW_DAYS))
        )

        return StreakOverview(
            streak=derived_practice_streak(
                stored, ordered_dates=ordered, current_run=run
            ),
            last_seven_days=tuple(
                CalendarDay(
                    day=day,
                    state=practice_day_state(
                        day,
                        today=today,
                        earliest=earliest,
                        practiced=practiced,
                        current_run=run_dates,
                    ),
                )
                for day in window
            ),
            today=today,
            is_today_pending=today not in practiced,
        )

    @staticmethod
    def _achievements_for(
        earned: tuple[EarnedAchievement, ...],
    ) -> AchievementsSummary:
        # The cascade can unlock several achievements sharing one instant, so
        # the id tiebreak is what fixes a stable order across repeated reads.
        ordered = sorted(
            earned, key=lambda item: (item.achieved_at, item.id), reverse=True
        )
        active_ids = {
            achievement.id
            for achievement in ACHIEVEMENT_CATALOG
            if achievement.is_active
        }
        return AchievementsSummary(
            recent=tuple(
                RecentAchievement(
                    achievement_id=item.achievement_id,
                    name=item.achievement_name,
                    criterion_label=achievement_criterion_label(
                        item.criterion.kind, item.criterion.target
                    ),
                    xp_reward=item.xp_reward,
                    achieved_at=item.achieved_at,
                )
                for item in ordered[:_RECENT_LIMIT]
            ),
            obtained_count=sum(
                1 for item in earned if item.achievement_id in active_ids
            ),
            catalog_count=len(active_ids),
        )
