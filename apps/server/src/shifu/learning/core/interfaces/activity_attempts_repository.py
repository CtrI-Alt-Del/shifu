from datetime import datetime
from typing import Protocol

from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import ActivityAttemptKind


class ActivityAttemptsRepository(Protocol):
    def find_by_id(self, attempt_id: str) -> ActivityAttempt | None: ...

    def find_account_id_by_attempt_id(self, attempt_id: str) -> str | None: ...

    def find_ids_by_account_id(self, account_id: str) -> list[str]:
        """Return attempt IDs owned by the account through their Goal."""
        ...

    def find_by_skill_experience_id_and_submission_key(
        self,
        skill_experience_id: str,
        submission_key: str,
    ) -> ActivityAttempt | None: ...

    def find_many_by_skill_experience_id_and_activity_id_and_kind(
        self,
        skill_experience_id: str,
        activity_id: str,
        kind: ActivityAttemptKind,
    ) -> list[ActivityAttempt]: ...

    def find_many_by_skill_experience_id(
        self,
        skill_experience_id: str,
    ) -> list[ActivityAttempt]:
        """Return attempts in submission order."""
        ...

    def find_many_by_skill_experience_id_and_diagnostic_run_id(
        self,
        skill_experience_id: str,
        diagnostic_run_id: str,
    ) -> list[ActivityAttempt]:
        """Return attempts in the diagnostic run's submission order."""
        ...

    def find_many_by_skill_experience_id_and_activity_id(
        self,
        skill_experience_id: str,
        activity_id: str,
    ) -> list[ActivityAttempt]:
        """Return activity attempts in submission order."""
        ...

    def find_many_latest_submitted_at_by_skill_experience_ids(
        self,
        skill_experience_ids: list[str],
    ) -> dict[str, datetime]:
        """Latest submission of any kind per experience; absent keys have none."""
        ...

    def find_many_evaluated_submitted_at_by_skill_experience_ids(
        self,
        skill_experience_ids: list[str],
        *,
        since: datetime,
    ) -> list[datetime]:
        """Submission instants of LEARNING and REVIEW attempts at or after
        ``since`` whose evaluation status is COMPLETED."""
        ...

    def add(self, attempt: ActivityAttempt) -> None: ...

    def add_many(self, attempts: list[ActivityAttempt]) -> None: ...

    def remove_diagnostic_by_experience(self, skill_experience_id: str) -> None: ...

    def remove_all(self) -> None: ...
