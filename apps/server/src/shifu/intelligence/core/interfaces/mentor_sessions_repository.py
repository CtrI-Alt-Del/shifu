from datetime import datetime
from typing import Protocol

from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.structures import (
    MentorSessionsPage,
    MentorSubmissionRecord,
)


class MentorSessionsRepository(Protocol):
    def find_submission(
        self, account_id: str, submission_key: str
    ) -> MentorSubmissionRecord | None: ...

    def find_submission_by_session_id(
        self, account_id: str, session_id: str
    ) -> MentorSubmissionRecord | None: ...

    def lock_submission(self, account_id: str, submission_key: str) -> None: ...

    def lock_session(self, account_id: str, session_id: str) -> None: ...

    def find_by_id(self, account_id: str, session_id: str) -> MentorSession | None: ...

    def find_by_id_for_update(
        self, account_id: str, session_id: str
    ) -> MentorSession | None: ...

    def find_many(
        self, account_id: str, search: str | None, cursor: str | None
    ) -> MentorSessionsPage: ...

    def add(
        self, session: MentorSession, submission_key: str, content_fingerprint: str
    ) -> None: ...

    def rename(self, session: MentorSession) -> None: ...

    def record_activity(self, session: MentorSession) -> None: ...

    def remove(self, session: MentorSession, deleted_at: datetime) -> None: ...

    def remove_all(self) -> None: ...
