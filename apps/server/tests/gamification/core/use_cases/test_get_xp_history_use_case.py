from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import (
    EarnedAchievementFaker,
    GamificationProfileFaker,
    XpGrantFaker,
)
from shifu.gamification.core.domain.enums import AchievementCriterionKind, XpSource
from shifu.gamification.core.domain.errors import GamificationProfileNotFoundError
from shifu.gamification.core.domain.entities import XpGrant
from shifu.gamification.core.domain.structures import AchievementCriterion, XpOrigin
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases.get_xp_history_use_case import (
    GetXpHistoryUseCase,
)

ACCOUNT_ID = 'account-1'
NOW = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)
EARLIER = datetime(2026, 1, 8, 12, 0, tzinfo=UTC)
EARLIEST = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)


def _grant(
    *,
    id: str,
    source: XpSource,
    label: str,
    reference_id: str = 'reference-1',
    amount: int = 10,
    granted_at: datetime = NOW,
    occurred_at: datetime | None = None,
) -> XpGrant:
    return XpGrantFaker.fake(
        id=id,
        account_id=ACCOUNT_ID,
        amount=amount,
        origin=XpOrigin(source=source, reference_id=reference_id, label=label),
        occurred_at=occurred_at if occurred_at is not None else granted_at,
        granted_at=granted_at,
    )


class TestGetXpHistoryUseCase:
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
            GamificationProfileFaker.fake(account_id=ACCOUNT_ID)
        )
        self.repositories.xp_grants.find_many_by_account_id.return_value = ()
        self.repositories.earned_achievements.find_many_by_account_id.return_value = ()
        self.subject = GetXpHistoryUseCase(self.database)

    def test_should_raise_when_the_account_has_no_profile(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        with pytest.raises(GamificationProfileNotFoundError):
            self.subject.execute(ACCOUNT_ID)

    def test_should_return_an_empty_history_when_no_grant_exists(self) -> None:
        history = self.subject.execute(ACCOUNT_ID)

        assert history.entries == ()
        assert history.total_xp == 0

    def test_should_preserve_the_repository_order_newest_concession_first(
        self,
    ) -> None:
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(id='c', source=XpSource.DIAGNOSIS, label='Newest', granted_at=NOW),
            _grant(
                id='b', source=XpSource.DIAGNOSIS, label='Middle', granted_at=EARLIER
            ),
            _grant(
                id='a', source=XpSource.DIAGNOSIS, label='Oldest', granted_at=EARLIEST
            ),
        )

        history = self.subject.execute(ACCOUNT_ID)

        assert [entry.title for entry in history.entries] == [
            'Newest',
            'Middle',
            'Oldest',
        ]
        assert [entry.grant_id for entry in history.entries] == ['c', 'b', 'a']

    def test_should_keep_both_records_of_a_shared_concession_instant(self) -> None:
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(id='b', source=XpSource.ACHIEVEMENT, label='Second', granted_at=NOW),
            _grant(id='a', source=XpSource.ACHIEVEMENT, label='First', granted_at=NOW),
        )

        history = self.subject.execute(ACCOUNT_ID)

        assert [entry.grant_id for entry in history.entries] == ['b', 'a']
        assert len(history.entries) == 2

    def test_should_sum_the_total_from_the_returned_records(self) -> None:
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(id='c', source=XpSource.DIAGNOSIS, label='A', amount=60),
            _grant(id='b', source=XpSource.SKILL_COMPLETION, label='B', amount=100),
            _grant(id='a', source=XpSource.COMPETENCY_MASTERY, label='C', amount=50),
        )

        history = self.subject.execute(ACCOUNT_ID)

        assert history.total_xp == 210
        assert history.total_xp == sum(entry.amount for entry in history.entries)

    @pytest.mark.parametrize(
        ('source', 'expected_detail'),
        [
            (XpSource.ACTIVITY, 'Atividade'),
            (XpSource.DIAGNOSIS, 'Diagnóstico concluído'),
            (XpSource.COMPETENCY_MASTERY, 'Primeiro domínio de Competência'),
            (XpSource.SKILL_COMPLETION, 'Habilidade concluída'),
        ],
    )
    def test_should_derive_the_descriptor_from_the_source(
        self, source: XpSource, expected_detail: str
    ) -> None:
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(id='a', source=source, label='Subject'),
        )

        history = self.subject.execute(ACCOUNT_ID)

        assert history.entries[0].detail == expected_detail
        assert history.entries[0].source is source

    def test_should_describe_an_achievement_with_its_own_earned_criterion(
        self,
    ) -> None:
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(
                id='a',
                source=XpSource.ACHIEVEMENT,
                label='Consistência II',
                reference_id='consistencia-ii',
            ),
        )
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            EarnedAchievementFaker.fake(
                account_id=ACCOUNT_ID,
                achievement_id='consistencia-ii',
                achievement_name='Consistência II',
                criterion=AchievementCriterion.create(
                    kind=AchievementCriterionKind.LONGEST_STREAK, target=7
                ),
            ),
        )

        history = self.subject.execute(ACCOUNT_ID)

        assert history.entries[0].detail == 'Conquista · 7 dias consecutivos'
        assert history.entries[0].title == 'Consistência II'

    def test_should_degrade_to_the_bare_achievement_descriptor_without_an_earned_row(
        self,
    ) -> None:
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(
                id='a',
                source=XpSource.ACHIEVEMENT,
                label='Retirada',
                reference_id='desconhecida',
            ),
        )

        history = self.subject.execute(ACCOUNT_ID)

        assert history.entries[0].detail == 'Conquista'

    def test_should_return_a_pre_delivery_label_unchanged(self) -> None:
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(
                id='a',
                source=XpSource.DIAGNOSIS,
                label='Diagnóstico concluído: Lógica de programação',
            ),
        )

        history = self.subject.execute(ACCOUNT_ID)

        assert (
            history.entries[0].title == 'Diagnóstico concluído: Lógica de programação'
        )
        assert history.entries[0].detail == 'Diagnóstico concluído'

    def test_should_carry_both_dates_separately(self) -> None:
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(
                id='a',
                source=XpSource.DIAGNOSIS,
                label='Subject',
                granted_at=NOW,
                occurred_at=EARLIEST,
            ),
        )

        history = self.subject.execute(ACCOUNT_ID)

        assert history.entries[0].occurred_at == EARLIEST
        assert history.entries[0].granted_at == NOW

    def test_should_query_every_repository_with_the_owning_account_id(self) -> None:
        """Account isolation (RF-07) is structural: every read is filtered by
        the account id taken from the verified session."""
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(id='a', source=XpSource.ACHIEVEMENT, label='Subject'),
        )

        self.subject.execute(ACCOUNT_ID)

        self.repositories.profiles.find_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.xp_grants.find_many_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        earned_reads = self.repositories.earned_achievements.find_many_by_account_id
        earned_reads.assert_called_once_with(ACCOUNT_ID)

    def test_should_not_mutate_any_repository_while_reading(self) -> None:
        self.repositories.xp_grants.find_many_by_account_id.return_value = (
            _grant(id='a', source=XpSource.DIAGNOSIS, label='Subject'),
        )

        self.subject.execute(ACCOUNT_ID)

        self.repositories.xp_grants.add.assert_not_called()
        self.repositories.xp_grants.remove_many_by_account_id.assert_not_called()
        self.repositories.profiles.update.assert_not_called()
        self.repositories.earned_achievements.try_add.assert_not_called()
        self.repositories.rewarded_milestones.try_add.assert_not_called()
