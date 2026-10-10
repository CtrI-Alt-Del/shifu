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
    XpSource,
)
from shifu.gamification.core.domain.structures import AchievementCriterion, XpOrigin
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import GrantXpUseCase
from shifu.shared.core.interfaces import IdentifierProvider

ACCOUNT_ID = 'account-1'
GRANT_ID = 'grant-1'
NOW = datetime(2026, 1, 1, tzinfo=UTC)
OCCURRED_AT = datetime(2025, 12, 1, tzinfo=UTC)
PROFILE_UPDATED_AT = datetime(2025, 1, 1, tzinfo=UTC)

_DIAGNOSTIC_ORIGIN = XpOrigin(
    source=XpSource.DIAGNOSIS, reference_id='skill-1', label='Diagnóstico'
)
_MASTERY_ORIGIN = XpOrigin(
    source=XpSource.COMPETENCY_MASTERY,
    reference_id='competency-1',
    label='Competência dominada',
)


class TestGrantXpUseCase:
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
        self.identifier_provider = create_autospec(IdentifierProvider, instance=True)
        self._next_id = 0
        self.identifier_provider.generate.side_effect = self._generate_id
        self.repositories.earned_achievements.find_many_by_account_id.return_value = ()
        self.repositories.rewarded_milestones.count_by_account_id_and_kind.return_value = 0
        self.subject = GrantXpUseCase(self.database, self.identifier_provider)

    def _generate_id(self) -> str:
        self._next_id += 1
        return f'generated-{self._next_id}'

    def test_should_no_op_when_profile_is_missing(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        self.subject.execute(
            ACCOUNT_ID,
            GRANT_ID,
            25,
            _DIAGNOSTIC_ORIGIN,
            'skill-experience-1',
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

        self.repositories.xp_grants.add.assert_not_called()
        self.repositories.profiles.update.assert_not_called()
        self.repositories.earned_achievements.try_add.assert_not_called()

    def test_should_apply_xp_and_persist_the_grant_when_no_achievement_unlocks(
        self,
    ) -> None:
        profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID, total_xp=0, level=1, created_at=PROFILE_UPDATED_AT
        )
        self.repositories.profiles.find_by_account_id.return_value = profile

        self.subject.execute(
            ACCOUNT_ID,
            GRANT_ID,
            25,
            _DIAGNOSTIC_ORIGIN,
            'skill-experience-1',
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

        self.repositories.xp_grants.add.assert_called_once()
        grant = self.repositories.xp_grants.add.call_args.args[0]
        assert grant.id == GRANT_ID
        assert grant.account_id == ACCOUNT_ID
        assert grant.amount == 25
        assert grant.origin == _DIAGNOSTIC_ORIGIN
        assert grant.fact_id == 'skill-experience-1'
        assert grant.occurred_at == OCCURRED_AT
        assert grant.granted_at == NOW
        assert profile.total_xp == 25
        assert profile.level == 1
        self.repositories.profiles.update.assert_called_once_with(profile)
        self.repositories.earned_achievements.try_add.assert_not_called()

    def test_should_raise_level_when_total_xp_crosses_a_threshold(self) -> None:
        profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID, total_xp=290, level=2, created_at=PROFILE_UPDATED_AT
        )
        self.repositories.profiles.find_by_account_id.return_value = profile

        self.subject.execute(
            ACCOUNT_ID,
            GRANT_ID,
            10,
            _DIAGNOSTIC_ORIGIN,
            'skill-experience-1',
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

        assert profile.total_xp == 300
        assert profile.level == 3

    def test_should_never_decrease_level_on_a_subsequent_grant(self) -> None:
        profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID, total_xp=310, level=3, created_at=PROFILE_UPDATED_AT
        )
        self.repositories.profiles.find_by_account_id.return_value = profile

        self.subject.execute(
            ACCOUNT_ID,
            GRANT_ID,
            5,
            _DIAGNOSTIC_ORIGIN,
            'skill-experience-1',
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

        assert profile.total_xp == 315
        assert profile.level == 3

    def test_should_unlock_level_and_count_achievements_in_the_same_cascade(
        self,
    ) -> None:
        # 50 * 5 * 4 = 1000 is the level-5 threshold; crossing it together with
        # a diagnostic count of 1 satisfies 'ascendente-i' (level 5) and
        # 'primeiro-passo' (1 diagnostic) in the very same pass.
        profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID, total_xp=990, level=4, created_at=PROFILE_UPDATED_AT
        )
        self.repositories.profiles.find_by_account_id.return_value = profile
        self.repositories.rewarded_milestones.count_by_account_id_and_kind.side_effect = _counts(
            {MilestoneKind.DIAGNOSIS: 1}
        )

        self.subject.execute(
            ACCOUNT_ID,
            GRANT_ID,
            20,
            _DIAGNOSTIC_ORIGIN,
            'skill-experience-1',
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

        assert self.repositories.earned_achievements.try_add.call_count == 2
        unlocked_ids = {
            call.args[0].achievement_id
            for call in self.repositories.earned_achievements.try_add.call_args_list
        }
        assert unlocked_ids == {'primeiro-passo', 'ascendente-i'}
        # Total xp is the initial 990 plus the 20 diagnostic xp plus both
        # achievement rewards (25 and 50).
        assert profile.total_xp == 1085
        assert profile.level == 5
        # One XpGrant for the triggering fact, one per achievement reward.
        assert self.repositories.xp_grants.add.call_count == 3

    def test_should_not_grant_an_already_unlocked_achievement_again(self) -> None:
        profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID, total_xp=0, level=1, created_at=PROFILE_UPDATED_AT
        )
        self.repositories.profiles.find_by_account_id.return_value = profile
        existing = EarnedAchievementFaker.fake(
            account_id=ACCOUNT_ID,
            achievement_id='primeiro-passo',
            criterion=AchievementCriterion.create(
                kind=AchievementCriterionKind.DIAGNOSTICS_COMPLETED, target=1
            ),
        )
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            existing,
        )
        self.repositories.rewarded_milestones.count_by_account_id_and_kind.side_effect = _counts(
            {MilestoneKind.DIAGNOSIS: 1}
        )

        self.subject.execute(
            ACCOUNT_ID,
            GRANT_ID,
            10,
            _DIAGNOSTIC_ORIGIN,
            'skill-experience-1',
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

        self.repositories.earned_achievements.try_add.assert_not_called()
        assert profile.total_xp == 10

    def test_should_backdate_a_directly_triggered_unlock_and_now_date_a_cascaded_one(
        self,
    ) -> None:
        # amount=1 keeps level at 4 but satisfies 'primeiro-dominio' (1
        # Competencia dominada) directly from the triggering fact. That
        # achievement's own 25 XP reward then crosses the level-5 threshold
        # (50*5*4=1000), discovering 'ascendente-i' only as a cascade effect
        # of the achievement XP, not of the original fact.
        profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID, total_xp=975, level=4, created_at=PROFILE_UPDATED_AT
        )
        self.repositories.profiles.find_by_account_id.return_value = profile
        self.repositories.rewarded_milestones.count_by_account_id_and_kind.side_effect = _counts(
            {MilestoneKind.COMPETENCY_MASTERY: 1}
        )

        self.subject.execute(
            ACCOUNT_ID,
            GRANT_ID,
            1,
            _MASTERY_ORIGIN,
            'skill-experience-1',
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

        unlocks = {
            call.args[0].achievement_id: call.args[0]
            for call in self.repositories.earned_achievements.try_add.call_args_list
        }
        assert set(unlocks) == {'primeiro-dominio', 'ascendente-i'}
        assert unlocks['primeiro-dominio'].achieved_at == OCCURRED_AT
        assert unlocks['primeiro-dominio'].granted_at == NOW
        assert unlocks['ascendente-i'].achieved_at == NOW
        assert unlocks['ascendente-i'].granted_at == NOW
        # Total xp is the initial 975 plus the 1 fact xp plus both
        # achievement rewards (25 and 50).
        assert profile.total_xp == 1051
        assert profile.level == 5


def _counts(
    overrides: dict[MilestoneKind, int],
) -> Callable[[str, MilestoneKind], int]:
    def side_effect(account_id: str, kind: MilestoneKind) -> int:
        del account_id
        return overrides.get(kind, 0)

    return side_effect
