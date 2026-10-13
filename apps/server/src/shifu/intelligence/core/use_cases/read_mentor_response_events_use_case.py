from shifu.intelligence.core.domain.errors import (
    MentorInputInvalidError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.domain.structures import MentorResponseEvent
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import MentorAccessProvider


class ReadMentorResponseEventsUseCase:
    def __init__(
        self, database: IntelligenceDatabase, access_provider: MentorAccessProvider
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._access_provider: MentorAccessProvider = access_provider

    def execute(
        self, account_id: str, session_id: str, after_sequence: int
    ) -> tuple[MentorResponseEvent, ...]:
        if after_sequence < 0:
            raise MentorInputInvalidError
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            if session is None:
                raise MentorSessionNotFoundError
            grant = self._access_provider.authorize(account_id, f'read:{session_id}')
            self._access_provider.assert_current(grant)
            return repositories.mentor_response_events.find_after(
                account_id, session_id, after_sequence
            )
