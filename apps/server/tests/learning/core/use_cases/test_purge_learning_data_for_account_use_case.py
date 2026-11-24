from unittest.mock import create_autospec

from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.purge_learning_data_for_account_use_case import (
    LEARNING_ACCOUNT_ERASURE_EVENT_NAMES,
    PurgeLearningDataForAccountUseCase,
)


class TestPurgeLearningDataForAccountUseCase:
    def setup_method(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(
            LearningDatabaseRepositories,
            instance=True,
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = PurgeLearningDataForAccountUseCase(self.database)

    def test_should_remove_goal_owned_data_and_receipts_for_account(self) -> None:
        self.repositories.activity_attempts.find_ids_by_account_id.return_value = [
            'attempt-1',
            'attempt-2',
        ]
        self.subject.execute('account-1')

        self.database.transaction.assert_called_once()
        self.repositories.activity_attempts.find_ids_by_account_id.assert_called_once_with(
            'account-1'
        )
        self.repositories.events.remove_by_payload_values.assert_called_once_with(
            'learning/activity-submission.requested',
            'attempt_id',
            {'attempt-1', 'attempt-2'},
        )
        self.repositories.events.remove_by_account_id_and_names.assert_called_once_with(
            'account-1',
            LEARNING_ACCOUNT_ERASURE_EVENT_NAMES,
        )
        self.repositories.goals.remove_by_account_id.assert_called_once_with(
            'account-1'
        )
        self.repositories.mentor_action_receipts.remove_by_account_id.assert_called_once_with(
            'account-1'
        )

    def test_should_not_delete_data_for_another_account(self) -> None:
        self.subject.execute('account-1')

        self.repositories.activity_attempts.find_ids_by_account_id.assert_called_once_with(
            'account-1'
        )
        self.repositories.events.remove_by_account_id_and_names.assert_called_once_with(
            'account-1',
            LEARNING_ACCOUNT_ERASURE_EVENT_NAMES,
        )
        self.repositories.goals.remove_by_account_id.assert_called_once_with(
            'account-1'
        )
        self.repositories.mentor_action_receipts.remove_by_account_id.assert_called_once_with(
            'account-1'
        )
