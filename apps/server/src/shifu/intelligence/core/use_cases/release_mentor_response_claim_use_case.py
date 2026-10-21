from shifu.intelligence.core.interfaces import IntelligenceDatabase


class ReleaseMentorResponseClaimUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database = database

    def execute(self, attempt_id: str, execution_owner: str) -> None:
        with self._database.transaction() as repositories:
            repositories.mentor_response_attempts.release_claim(
                attempt_id, execution_owner
            )
