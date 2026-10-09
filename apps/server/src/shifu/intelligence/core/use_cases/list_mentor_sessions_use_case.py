import unicodedata

from shifu.intelligence.core.domain.structures import MentorSessionsPage
from shifu.intelligence.core.interfaces import IntelligenceDatabase


class ListMentorSessionsUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database = database

    def execute(
        self, account_id: str, search: str | None = None, cursor: str | None = None
    ) -> MentorSessionsPage:
        normalized_search = (
            self._normalize_search(search) if search is not None else None
        )
        with self._database.transaction() as repositories:
            return repositories.mentor_sessions.find_many(
                account_id, normalized_search, cursor
            )

    @staticmethod
    def _normalize_search(search: str) -> str:
        decomposed = unicodedata.normalize('NFKD', search.casefold())
        return ''.join(char for char in decomposed if not unicodedata.combining(char))
