from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import (
    EarnedAchievementFaker,
    GamificationProfileFaker,
)
from shifu.gamification.core.domain.enums import (
    AchievementCriterionKind,
    MilestoneKind,
)
from shifu.gamification.core.domain.structures import AchievementCriterion
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import ListAchievementsUseCase

ACCOUNT_ID = 'account-1'
NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestListAchievementsUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories,
            instance=True,
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(account_id=ACCOUNT_ID, total_xp=50, level=1)
        )
        self.repositories.earned_achievements.find_many_by_account_id.return_value = ()
        self.repositories.rewarded_milestones.count_by_account_id_and_kind.return_value = 0
        self.subject = ListAchievementsUseCase(self.database)

    def test_should_return_level_xp_and_xp_for_next_level(self) -> None:
        overview = self.subject.execute(ACCOUNT_ID)

        assert overview.level == 1
        assert overview.total_xp == 50
        # Level-2 threshold is 50 * 2 * 1 = 100.
        assert overview.xp_for_next_level == 50

    def test_should_list_all_catalog_entries_with_obtained_and_locked_states(
        self,
    ) -> None:
        earned_a = EarnedAchievementFaker.fake(
            account_id=ACCOUNT_ID,
            achievement_id='primeiro-passo',
            achievement_name='Primeiro Passo',
            criterion=AchievementCriterion.create(
                kind=AchievementCriterionKind.DIAGNOSTICS_COMPLETED, target=1
            ),
            xp_reward=25,
            achieved_at=NOW,
        )
        earned_b = EarnedAchievementFaker.fake(
            account_id=ACCOUNT_ID,
            achievement_id='primeiro-dominio',
            achievement_name='Primeiro Domínio',
            criterion=AchievementCriterion.create(
                kind=AchievementCriterionKind.COMPETENCIES_MASTERED, target=1
            ),
            xp_reward=25,
            achieved_at=NOW,
        )
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            earned_a,
            earned_b,
        )
        self.repositories.rewarded_milestones.count_by_account_id_and_kind.side_effect = _counts(
            {
                MilestoneKind.DIAGNOSIS: 1,
                MilestoneKind.COMPETENCY_MASTERY: 1,
            }
        )

        overview = self.subject.execute(ACCOUNT_ID)

        assert len(overview.achievements) == 12
        obtained = [a for a in overview.achievements if a.state == 'obtained']
        locked = [a for a in overview.achievements if a.state == 'locked']
        assert len(obtained) == 2
        assert len(locked) == 10
        assert {a.code for a in obtained} == {
            'primeiro-passo',
            'primeiro-dominio',
        }
        assert all(a.unlocked_at == NOW for a in obtained)
        assert all(a.progress_current is None for a in obtained)
        explorador = next(a for a in overview.achievements if a.code == 'explorador')
        assert explorador.state == 'locked'
        assert explorador.progress_current == 1
        assert explorador.progress_target == 5
        assert explorador.criterion_label == '5 diagnósticos concluídos'

    def test_should_mark_unknown_catalog_code_as_historical_only_for_holder(
        self,
    ) -> None:
        retired_earned = EarnedAchievementFaker.fake(
            account_id=ACCOUNT_ID,
            achievement_id='retired-achievement',
            achievement_name='Conquista Retirada',
            criterion=AchievementCriterion.create(
                kind=AchievementCriterionKind.DIAGNOSTICS_COMPLETED, target=1
            ),
            xp_reward=25,
            achieved_at=NOW,
        )
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            retired_earned,
        )

        overview = self.subject.execute(ACCOUNT_ID)

        historical = [a for a in overview.achievements if a.state == 'historical']
        assert len(historical) == 1
        historical_view = historical[0]
        assert historical_view.code == 'retired-achievement'
        assert historical_view.name == 'Conquista Retirada'
        assert historical_view.description == ''
        assert historical_view.xp_reward == 25
        assert historical_view.unlocked_at == NOW

        self.repositories.earned_achievements.find_many_by_account_id.return_value = ()
        other_overview = self.subject.execute('other-account')
        assert all(
            achievement.code != 'retired-achievement'
            for achievement in other_overview.achievements
        )

    def test_should_preserve_rewards_regardless_of_removed_learning_content(
        self,
    ) -> None:
        earned = EarnedAchievementFaker.fake(
            account_id=ACCOUNT_ID,
            achievement_id='primeira-jornada',
            achievement_name='Primeira Jornada',
            criterion=AchievementCriterion.create(
                kind=AchievementCriterionKind.SKILLS_COMPLETED, target=1
            ),
            xp_reward=50,
            achieved_at=NOW,
        )
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            earned,
        )
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(account_id=ACCOUNT_ID, total_xp=150)
        )

        overview = self.subject.execute(ACCOUNT_ID)

        assert overview.total_xp == 150
        granted = next(a for a in overview.achievements if a.code == 'primeira-jornada')
        assert granted.state == 'obtained'
        assert granted.unlocked_at == NOW


def _counts(
    overrides: dict[MilestoneKind, int],
) -> Callable[[str, MilestoneKind], int]:
    def side_effect(account_id: str, kind: MilestoneKind) -> int:
        del account_id
        return overrides.get(kind, 0)

    return side_effect
