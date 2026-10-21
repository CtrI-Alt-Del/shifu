from typing import Protocol

from shifu.intelligence.core.domain.entities import MentorSessionSummary


class MentorSessionSummariesRepository(Protocol):
    def find_ready(
        self, account_id: str, session_id: str
    ) -> MentorSessionSummary | None: ...

    def find_processing_for_update(
        self, account_id: str, session_id: str
    ) -> MentorSessionSummary | None: ...

    def find_failed(
        self, account_id: str, session_id: str
    ) -> MentorSessionSummary | None: ...

    def next_version(self, session_id: str) -> int: ...

    def add(self, summary: MentorSessionSummary) -> None:
        """Insert a summary; a conflict with the active-row index raises a typed error."""
        ...

    def update(self, summary: MentorSessionSummary) -> None: ...

    def remove_superseded(self, session_id: str, keep_id: str) -> None:
        """Remove every ready and failed row of the session except ``keep_id``."""
        ...

    def remove_superseded_failures(self, session_id: str, keep_id: str) -> None:
        """Remove every failed row of the session except ``keep_id``; keep ready rows."""
        ...

    def remove(self, summary_id: str) -> None: ...

    def remove_by_session_id(self, session_id: str) -> None: ...

    def remove_by_account_id(self, account_id: str) -> int: ...

    def remove_all(self) -> None: ...
