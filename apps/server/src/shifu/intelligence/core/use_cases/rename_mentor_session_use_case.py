from shifu.intelligence.core.domain.errors import (
    MentorInputInvalidError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import ClockProvider


class RenameMentorSessionUseCase:
    def __init__(
        self, database: IntelligenceDatabase, clock_provider: ClockProvider
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider

    def execute(self, account_id: str, session_id: str, title: str) -> MentorSession:
        normalized_title = title.strip()
        if not normalized_title or len(normalized_title) > 120:
            raise MentorInputInvalidError

        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            if session is None:
                raise MentorSessionNotFoundError
            session.title = normalized_title
            session.updated_at = self._clock_provider.now()
            repositories.mentor_sessions.rename(session)
            return session
