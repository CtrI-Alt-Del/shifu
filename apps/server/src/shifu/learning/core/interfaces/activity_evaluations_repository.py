from typing import Protocol

from shifu.learning.core.domain.entities import ActivityEvaluation


class ActivityEvaluationsRepository(Protocol):
    def find_by_id(
        self,
        evaluation_id: str,
    ) -> ActivityEvaluation | None: ...

    def find_by_attempt_id(
        self,
        attempt_id: str,
    ) -> ActivityEvaluation | None: ...

    def find_unresolved_by_skill_experience_id(
        self,
        skill_experience_id: str,
    ) -> ActivityEvaluation | None:
        """Find the pending or failed evaluation that blocks new attempts."""
        ...

    def find_many_by_skill_experience_id_and_activity_id(
        self,
        skill_experience_id: str,
        activity_id: str,
    ) -> list[ActivityEvaluation]:
        """Return completed and unresolved evaluations in attempt order."""
        ...

    def add(self, evaluation: ActivityEvaluation) -> None: ...

    def add_many(self, evaluations: list[ActivityEvaluation]) -> None: ...

    def update(self, evaluation: ActivityEvaluation) -> None: ...

    def remove_all(self) -> None: ...
