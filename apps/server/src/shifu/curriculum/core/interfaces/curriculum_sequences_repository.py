from typing import Protocol

from shifu.curriculum.core.domain.structures import CurriculumSequence


class CurriculumSequencesRepository(Protocol):
    def find_by_competency_id(
        self,
        competency_id: str,
    ) -> CurriculumSequence | None: ...

    def add_many(self, sequences: list[CurriculumSequence]) -> None: ...

    def remove_all(self) -> None: ...
