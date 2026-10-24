from contextlib import AbstractContextManager
from typing import Protocol

from shifu.gamification.core.interfaces.activity_xp_balances_repository import (
    ActivityXpBalancesRepository,
)
from shifu.gamification.core.interfaces.activity_xp_recognitions_repository import (
    ActivityXpRecognitionsRepository,
)
from shifu.gamification.core.interfaces.earned_achievements_repository import (
    EarnedAchievementsRepository,
)
from shifu.gamification.core.interfaces.gamification_profiles_repository import (
    GamificationProfilesRepository,
)
from shifu.gamification.core.interfaces.practice_days_repository import (
    PracticeDaysRepository,
)
from shifu.gamification.core.interfaces.rewarded_milestones_repository import (
    RewardedMilestonesRepository,
)
from shifu.gamification.core.interfaces.xp_grants_repository import (
    XpGrantsRepository,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.interfaces import EventsRepository


@structure
class GamificationDatabaseRepositories:
    profiles: GamificationProfilesRepository
    xp_grants: XpGrantsRepository
    earned_achievements: EarnedAchievementsRepository
    rewarded_milestones: RewardedMilestonesRepository
    practice_days: PracticeDaysRepository
    activity_xp_balances: ActivityXpBalancesRepository
    activity_xp_recognitions: ActivityXpRecognitionsRepository
    events: EventsRepository


class GamificationDatabase(Protocol):
    def transaction(
        self,
    ) -> AbstractContextManager[GamificationDatabaseRepositories]:
        """Open the sole transaction boundary for one Gamification operation."""
        ...
