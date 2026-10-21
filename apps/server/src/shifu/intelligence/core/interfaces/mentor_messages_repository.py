from typing import Protocol

from shifu.intelligence.core.domain.entities import MentorMessage
from shifu.intelligence.core.domain.structures import (
    MentorMessagesPage,
    MentorMessageVolume,
    MentorSummaryBoundary,
)


class MentorMessagesRepository(Protocol):
    def find_many(
        self, account_id: str, session_id: str, cursor: str | None
    ) -> MentorMessagesPage: ...

    def find_by_id(
        self, account_id: str, session_id: str, message_id: str
    ) -> MentorMessage | None: ...

    def find_response(
        self, account_id: str, session_id: str, learner_message_id: str
    ) -> MentorMessage | None: ...

    def find_pending_learner_message_id(
        self, account_id: str, session_id: str
    ) -> str | None: ...

    def find_all(
        self, account_id: str, session_id: str
    ) -> tuple[MentorMessage, ...]: ...

    def measure_unsummarized(
        self,
        account_id: str,
        session_id: str,
        after: MentorSummaryBoundary | None,
        keep_recent: int,
    ) -> MentorMessageVolume:
        """Count messages after ``after`` and outside the ``keep_recent`` newest."""
        ...

    def find_first_message_id(self, account_id: str, session_id: str) -> str | None:
        """Id of the conversation's first message by (created_at, id), if any."""
        ...

    def find_range(
        self,
        account_id: str,
        session_id: str,
        after: MentorSummaryBoundary | None,
        until: MentorSummaryBoundary | None = None,
    ) -> tuple[MentorMessage, ...]:
        """Messages strictly after ``after`` up to and including ``until``, ordered."""
        ...

    def find_by_ids(
        self, account_id: str, session_id: str, message_ids: tuple[str, ...]
    ) -> tuple[MentorMessage, ...]:
        """Only messages of that session, ordered by (created_at, id)."""
        ...

    def add(self, message: MentorMessage) -> None: ...

    def remove_by_session_id(self, session_id: str) -> None: ...

    def remove_all(self) -> None: ...
