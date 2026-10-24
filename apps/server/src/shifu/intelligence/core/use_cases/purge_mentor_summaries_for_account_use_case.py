from shifu.intelligence.core.interfaces import IntelligenceDatabase


class PurgeMentorSummariesForAccountUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> int:
        """Remove every summary row of the account; repeated calls return 0."""
        with self._database.transaction() as repositories:
            return repositories.mentor_session_summaries.remove_by_account_id(
                account_id
            )
