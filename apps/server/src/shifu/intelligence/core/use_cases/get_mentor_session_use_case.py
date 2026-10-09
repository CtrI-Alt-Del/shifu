from shifu.intelligence.core.domain.errors import MentorSessionNotFoundError
from shifu.intelligence.core.domain.structures import MentorSessionDetail
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_detail import load_mentor_detail


class GetMentorSessionUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database = database

    def execute(
        self, account_id: str, session_id: str, cursor: str | None = None
    ) -> MentorSessionDetail:
        detail = load_mentor_detail(self._database, account_id, session_id, cursor)
        if detail is None:
            raise MentorSessionNotFoundError
        return detail
