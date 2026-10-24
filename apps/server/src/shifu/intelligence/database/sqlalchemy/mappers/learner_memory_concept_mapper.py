from typing import ClassVar

from shifu.intelligence.core.domain.structures import LearnerMemoryConcept
from shifu.intelligence.database.sqlalchemy.models import LearnerMemoryConceptModel


class LearnerMemoryConceptMapper:
    MAX_CONCEPTS: ClassVar[int] = 3

    @staticmethod
    def to_concept(model: LearnerMemoryConceptModel) -> LearnerMemoryConcept:
        return LearnerMemoryConcept(key=model.concept_key, label=model.label)

    @staticmethod
    def to_models(
        memory_id: str, concepts: tuple[LearnerMemoryConcept, ...]
    ) -> list[LearnerMemoryConceptModel]:
        """Keep the first occurrence of each key and at most three concepts."""
        unique: dict[str, LearnerMemoryConcept] = {}
        for concept in concepts:
            unique.setdefault(concept.key, concept)
        return [
            LearnerMemoryConceptModel(
                memory_id=memory_id,
                concept_key=concept.key,
                label=concept.label,
                position=position,
            )
            for position, concept in enumerate(
                list(unique.values())[: LearnerMemoryConceptMapper.MAX_CONCEPTS]
            )
        ]
