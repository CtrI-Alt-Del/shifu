from shifu.intelligence.core.interfaces import IntelligenceDatabase


class PurgeMentorActionProposalsForAccountUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database: IntelligenceDatabase = database

    def execute(self, account_id: str) -> int:
        """Remove every proposal of the account; repeated calls return 0."""
        with self._database.transaction() as repositories:
            return repositories.mentor_action_proposals.remove_by_account_id(account_id)
