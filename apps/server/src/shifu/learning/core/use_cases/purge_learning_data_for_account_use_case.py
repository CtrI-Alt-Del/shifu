from shifu.learning.core.interfaces import LearningDatabase

LEARNING_ACCOUNT_ERASURE_EVENT_NAMES = {
    'learning/activity-evaluated',
    'learning/competency-mastery-lost',
    'learning/competency-mastered',
    'learning/diagnostic-completed',
    'learning/mentor-skill-action-resolved',
    'learning/skill-completed',
}


class PurgeLearningDataForAccountUseCase:
    """Delete all Learning-owned data for one closed account."""

    def __init__(self, database: LearningDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> None:
        with self._database.transaction() as repositories:
            attempt_ids = repositories.activity_attempts.find_ids_by_account_id(
                account_id
            )
            repositories.events.remove_by_payload_values(
                'learning/activity-submission.requested',
                'attempt_id',
                set(attempt_ids),
            )
            repositories.events.remove_by_account_id_and_names(
                account_id,
                LEARNING_ACCOUNT_ERASURE_EVENT_NAMES,
            )
            repositories.goals.remove_by_account_id(account_id)
            repositories.mentor_action_receipts.remove_by_account_id(account_id)
