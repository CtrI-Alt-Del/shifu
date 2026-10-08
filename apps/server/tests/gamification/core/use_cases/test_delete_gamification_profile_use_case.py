from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import DeleteGamificationProfileUseCase

ACCOUNT_ID = 'account-1'


class TestDeleteGamificationProfileUseCase:
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
        self.subject = DeleteGamificationProfileUseCase(self.database)

    def test_should_purge_all_gamification_rows_when_profile_exists(self) -> None:
        profile = GamificationProfileFaker.fake(account_id=ACCOUNT_ID)
        self.repositories.profiles.find_by_account_id.return_value = profile

        self.subject.execute(ACCOUNT_ID)

        self.repositories.profiles.remove.assert_called_once_with(profile)
        self.repositories.xp_grants.remove_many_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.earned_achievements.remove_many_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.rewarded_milestones.remove_many_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )

    def test_should_no_op_when_profile_is_absent(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        self.subject.execute(ACCOUNT_ID)

        self.repositories.profiles.remove.assert_not_called()
        self.repositories.xp_grants.remove_many_by_account_id.assert_not_called()
        self.repositories.earned_achievements.remove_many_by_account_id.assert_not_called()
        self.repositories.rewarded_milestones.remove_many_by_account_id.assert_not_called()
