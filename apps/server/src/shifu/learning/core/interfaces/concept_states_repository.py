from datetime import datetime
from typing import Protocol

from shifu.learning.core.domain.structures import AdaptiveConceptState


class ConceptStatesRepository(Protocol):
    def find_many_by_skill_experience_id(
        self, skill_experience_id: str
    ) -> list[AdaptiveConceptState]: ...

    def upsert_many(
        self,
        skill_experience_id: str,
        competency_by_concept_id: dict[str, str],
        states: tuple[AdaptiveConceptState, ...],
        updated_at: datetime,
    ) -> None: ...
