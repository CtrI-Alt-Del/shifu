from typing import Protocol

from shifu.curriculum.core.domain.entities import Concept


class ConceptsRepository(Protocol):
    def find_many_by_skill_id(self, skill_id: str) -> list[Concept]: ...

    def add_many(self, concepts: list[Concept]) -> None: ...

    def remove_all(self) -> None: ...
