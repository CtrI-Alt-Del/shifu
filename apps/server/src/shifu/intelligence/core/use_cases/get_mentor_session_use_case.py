from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.intelligence.core.domain.errors import (
    MentorCursorInvalidError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.domain.structures import MentorSessionDetail
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_detail import load_mentor_detail


class GetMentorSessionUseCase:
    def __init__(
        self, database: IntelligenceDatabase, access_provider: MentorAccessProvider
    ) -> None:
        self._database = database
        self._access_provider: MentorAccessProvider = access_provider

    def execute(
        self, account_id: str, session_id: str, cursor: str | None = None
    ) -> MentorSessionDetail:
        grant = self._access_provider.authorize(account_id, f'read:{session_id}')
        self._access_provider.assert_current(grant)
        try:
            detail = load_mentor_detail(self._database, account_id, session_id, cursor)
        except (TypeError, ValueError) as error:
            if cursor is None:
                raise
            raise MentorCursorInvalidError from error
        if detail is None:
            raise MentorSessionNotFoundError
        return detail
