from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import CreateGamificationProfileUseCase
from shifu.shared.core.interfaces import IdentifierProvider

ACCOUNT_ID = 'account-1'
PROFILE_ID = 'profile-1'
NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestCreateGamificationProfileUseCase:
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
        self.repositories.profiles.find_by_account_id.return_value = None
        self.identifier_provider = create_autospec(IdentifierProvider, instance=True)
        self.identifier_provider.generate.return_value = PROFILE_ID
        self.subject = CreateGamificationProfileUseCase(
            self.database, self.identifier_provider
        )

    def test_should_create_profile_with_zero_xp_and_level_one_when_absent(
        self,
    ) -> None:
        self.subject.execute(ACCOUNT_ID, now=NOW)

        self.repositories.profiles.add.assert_called_once()
        created = self.repositories.profiles.add.call_args.args[0]
        assert created.id == PROFILE_ID
        assert created.account_id == ACCOUNT_ID
        assert created.total_xp == 0
        assert created.level == 1
        assert created.streak == PracticeStreak()
        assert created.created_at == NOW
        assert created.updated_at == NOW

    def test_should_be_idempotent_when_profile_already_exists(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(id=PROFILE_ID, account_id=ACCOUNT_ID)
        )

        self.subject.execute(ACCOUNT_ID, now=NOW)

        self.repositories.profiles.add.assert_not_called()
