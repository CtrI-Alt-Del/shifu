from typing import Protocol

from shifu.learning.core.domain.entities import CompetencyProgress


class CompetencyProgressesRepository(Protocol):
    def find_by_id(
        self,
        competency_progress_id: str,
    ) -> CompetencyProgress | None: ...

    def find_by_skill_experience_id_and_competency_id(
        self,
        skill_experience_id: str,
        competency_id: str,
    ) -> CompetencyProgress | None: ...

    def find_many_by_skill_experience_id(
        self,
        skill_experience_id: str,
    ) -> list[CompetencyProgress]: ...

    def add(self, competency_progress: CompetencyProgress) -> None: ...

    def add_many(self, competency_progresses: list[CompetencyProgress]) -> None: ...

    def replace(self, competency_progress: CompetencyProgress) -> None: ...
