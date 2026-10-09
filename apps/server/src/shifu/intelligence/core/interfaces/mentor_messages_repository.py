from typing import Protocol

from shifu.intelligence.core.domain.entities import MentorMessage
from shifu.intelligence.core.domain.structures import MentorMessagesPage


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

    def add(self, message: MentorMessage) -> None: ...

    def remove_by_session_id(self, session_id: str) -> None: ...

    def remove_all(self) -> None: ...
