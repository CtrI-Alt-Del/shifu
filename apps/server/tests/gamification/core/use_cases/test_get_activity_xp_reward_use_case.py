from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import (
    ActivityXpBalanceFaker,
    ActivityXpRecognitionFaker,
    GamificationProfileFaker,
)
from shifu.gamification.core.domain.enums import ActivityXpRewardState
from shifu.gamification.core.domain.errors import GamificationProfileNotFoundError
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases.get_activity_xp_reward_use_case import (
    GetActivityXpRewardUseCase,
)

ACCOUNT_ID = 'account-1'
ACTIVITY_ID = 'activity-1'
OTHER_ACTIVITY_ID = 'activity-2'
ATTEMPT_ID = 'attempt-1'


class TestGetActivityXpRewardUseCase:
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
        self.repositories.activity_xp_recognitions.find_by_account_id_and_attempt_id.return_value = None
        self.repositories.activity_xp_balances.find_by_account_id_and_activity_id.return_value = None
        self.subject = GetActivityXpRewardUseCase(self.database)

    def test_should_report_pending_without_a_recognition(self) -> None:
        reward = self.subject.execute(ACCOUNT_ID, ACTIVITY_ID, ATTEMPT_ID)

        assert reward.state is ActivityXpRewardState.PENDING
        assert reward.additional_xp == 0
        assert reward.granted_xp == 0
        assert reward.maximum_xp is None
        assert reward.activity_id == ACTIVITY_ID
        assert reward.attempt_id == ATTEMPT_ID

    def test_should_report_pending_with_the_existing_balance_numbers(self) -> None:
        self.repositories.activity_xp_balances.find_by_account_id_and_activity_id.return_value = ActivityXpBalanceFaker.fake(
            account_id=ACCOUNT_ID,
            activity_id=ACTIVITY_ID,
            maximum_xp=10,
            granted_xp=6,
        )

        reward = self.subject.execute(ACCOUNT_ID, ACTIVITY_ID, ATTEMPT_ID)

        assert reward.state is ActivityXpRewardState.PENDING
        assert reward.granted_xp == 6
        assert reward.maximum_xp == 10

    def test_should_report_granted_for_a_positive_recognition(self) -> None:
        self.repositories.activity_xp_recognitions.find_by_account_id_and_attempt_id.return_value = ActivityXpRecognitionFaker.fake(
            account_id=ACCOUNT_ID,
            activity_id=ACTIVITY_ID,
            attempt_id=ATTEMPT_ID,
            granted_xp=6,
            xp_grant_id='grant-1',
        )
        self.repositories.activity_xp_balances.find_by_account_id_and_activity_id.return_value = ActivityXpBalanceFaker.fake(
            account_id=ACCOUNT_ID,
            activity_id=ACTIVITY_ID,
            maximum_xp=10,
            granted_xp=6,
        )

        reward = self.subject.execute(ACCOUNT_ID, ACTIVITY_ID, ATTEMPT_ID)

        assert reward.state is ActivityXpRewardState.GRANTED
        assert reward.additional_xp == 6
        assert reward.granted_xp == 6
        assert reward.maximum_xp == 10

    def test_should_report_no_additional_for_a_zero_recognition(self) -> None:
        self.repositories.activity_xp_recognitions.find_by_account_id_and_attempt_id.return_value = ActivityXpRecognitionFaker.fake(
            account_id=ACCOUNT_ID,
            activity_id=ACTIVITY_ID,
            attempt_id=ATTEMPT_ID,
            granted_xp=0,
            xp_grant_id=None,
        )
        self.repositories.activity_xp_balances.find_by_account_id_and_activity_id.return_value = ActivityXpBalanceFaker.fake(
            account_id=ACCOUNT_ID,
            activity_id=ACTIVITY_ID,
            maximum_xp=10,
            granted_xp=10,
        )

        reward = self.subject.execute(ACCOUNT_ID, ACTIVITY_ID, ATTEMPT_ID)

        assert reward.state is ActivityXpRewardState.NO_ADDITIONAL
        assert reward.additional_xp == 0
        assert reward.granted_xp == 10
        assert reward.maximum_xp == 10

    def test_should_read_the_balance_by_the_recognitions_own_activity_id(
        self,
    ) -> None:
        """A mismatched (attempt, activity) pair in the request must not mix one
        attempt's additional_xp with a different Activity's cumulative numbers."""
        self.repositories.activity_xp_recognitions.find_by_account_id_and_attempt_id.return_value = ActivityXpRecognitionFaker.fake(
            account_id=ACCOUNT_ID,
            activity_id=OTHER_ACTIVITY_ID,
            attempt_id=ATTEMPT_ID,
            granted_xp=6,
            xp_grant_id='grant-1',
        )

        self.subject.execute(ACCOUNT_ID, ACTIVITY_ID, ATTEMPT_ID)

        self.repositories.activity_xp_balances.find_by_account_id_and_activity_id.assert_called_once_with(
            ACCOUNT_ID, OTHER_ACTIVITY_ID
        )

    def test_should_raise_when_profile_is_missing(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        with pytest.raises(GamificationProfileNotFoundError):
            self.subject.execute(ACCOUNT_ID, ACTIVITY_ID, ATTEMPT_ID)

    def test_should_perform_no_write(self) -> None:
        self.subject.execute(ACCOUNT_ID, ACTIVITY_ID, ATTEMPT_ID)

        self.repositories.activity_xp_balances.add.assert_not_called()
        self.repositories.activity_xp_balances.update.assert_not_called()
        self.repositories.activity_xp_recognitions.try_add.assert_not_called()
