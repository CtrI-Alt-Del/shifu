from datetime import datetime
from typing import Protocol
from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.domain.structures import MentorInferenceUsage


class MentorResponseAttemptsRepository(Protocol):
    def journal_usage(
        self,
        attempt_id: str,
        owner: str,
        access_revision: str,
        usage: MentorInferenceUsage,
    ) -> bool: ...

    def read_usage(
        self, attempt_id: str
    ) -> tuple[MentorInferenceUsage, ...] | None: ...

    def inference_started(self, attempt_id: str) -> bool: ...

    def claim(
        self,
        attempt_id: str,
        owner: str,
        now: datetime,
        expires_at: datetime,
        access_revision: str,
    ) -> bool: ...

    def renew_claim(
        self,
        attempt_id: str,
        owner: str,
        now: datetime,
        expires_at: datetime,
        access_revision: str,
    ) -> bool: ...

    def has_claim(self, attempt_id: str, owner: str, now: datetime) -> bool: ...

    def release_claim(self, attempt_id: str, owner: str) -> None: ...

    def find_continuity(self, account_id: str, session_id: str) -> tuple[str, ...]: ...

    def update_references(
        self, attempt_id: str, reference_ids: tuple[str, ...], access_revision: str
    ) -> bool: ...

    def find_by_id(self, attempt_id: str) -> MentorResponseAttempt | None: ...

    def find_current(
        self, account_id: str, session_id: str
    ) -> MentorResponseAttempt | None: ...
    def find_by_id_for_update(
        self, attempt_id: str
    ) -> MentorResponseAttempt | None: ...
    def find_submission(
        self, account_id: str, session_id: str, submission_key: str
    ) -> tuple[MentorResponseAttempt, str] | None: ...
    def add(self, attempt: MentorResponseAttempt) -> None: ...
    def add_submission(
        self,
        account_id: str,
        session_id: str,
        submission_key: str,
        attempt_id: str,
        fingerprint: str,
    ) -> None: ...
    def transition(
        self,
        attempt_id: str,
        expected_status: MentorResponseStatus,
        new_status: MentorResponseStatus,
        access_revision: str,
    ) -> bool: ...
    def reserve_generation(
        self, attempt_id: str, block_key: str, access_revision: str
    ) -> bool: ...

    def remove_by_session_id(self, session_id: str) -> None: ...
