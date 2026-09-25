from typing import Protocol

from shifu.learning.core.domain.structures import ConceptObservation


class ConceptObservationsRepository(Protocol):
    def find_many_by_skill_experience_id(
        self, skill_experience_id: str
    ) -> list[ConceptObservation]: ...

    def find_many_by_attempt_id(self, attempt_id: str) -> list[ConceptObservation]: ...

    def add_many(
        self,
        skill_experience_id: str,
        competency_id: str,
        observations: tuple[ConceptObservation, ...],
    ) -> None: ...
