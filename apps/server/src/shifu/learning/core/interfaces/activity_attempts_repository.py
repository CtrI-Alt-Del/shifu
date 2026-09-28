from typing import Protocol

from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import ActivityAttemptKind


class ActivityAttemptsRepository(Protocol):
    def find_by_id(self, attempt_id: str) -> ActivityAttempt | None: ...

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

    def add(self, attempt: ActivityAttempt) -> None: ...

    def add_many(self, attempts: list[ActivityAttempt]) -> None: ...

    def remove_diagnostic_by_experience(self, skill_experience_id: str) -> None: ...

    def remove_all(self) -> None: ...
