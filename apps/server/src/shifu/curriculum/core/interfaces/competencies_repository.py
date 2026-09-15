from typing import Protocol

from shifu.curriculum.core.domain.entities import Competency


class CompetenciesRepository(Protocol):
    def find_by_id(self, competency_id: str) -> Competency | None: ...

    def find_many_by_skill_id(self, skill_id: str) -> list[Competency]:
        """Return Competencies in their official curricular position order."""
        ...
