from dataclasses import dataclass

from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.structures import (
    AdaptiveActivity,
    AdaptiveConcept,
    AdaptiveMaterial,
)
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumSkillSnapshot,
)


@dataclass(frozen=True, slots=True)
class AdaptivePolicyContext:
    competency_ids: tuple[str, ...]
    concepts: tuple[AdaptiveConcept, ...]
    activities: tuple[AdaptiveActivity, ...]
    materials: tuple[AdaptiveMaterial, ...]

    @classmethod
    def from_skill(cls, skill: CurriculumSkillSnapshot) -> 'AdaptivePolicyContext':
        ordered_competencies = tuple(
            sorted(skill.competencies, key=lambda item: (item.position, item.id))
        )
        concepts: list[AdaptiveConcept] = []
        activities: list[AdaptiveActivity] = []
        materials: list[AdaptiveMaterial] = []
        for competency in ordered_competencies:
            concepts.extend(
                AdaptiveConcept(
                    id=concept.id,
                    competency_id=competency.id,
                    position=concept.position,
                    prerequisite_ids=concept.prerequisite_ids,
                )
                for concept in sorted(
                    competency.concepts, key=lambda item: (item.position, item.id)
                )
            )
            for item in competency.items:
                if isinstance(item, CurriculumActivitySnapshot):
                    if item.activity_type != 'learning':
                        continue
                    activities.append(
                        AdaptiveActivity(
                            id=item.id,
                            competency_id=competency.id,
                            position=item.position,
                            difficulty=ActivityDifficulty(item.difficulty),
                            concept_ids=item.concept_ids,
                            required_concept_ids=item.required_concept_ids,
                            question_count_by_concept=item.question_count_by_concept,
                            executable_concept_evidence=item.executable_concept_evidence,
                        )
                    )
                else:
                    materials.append(
                        AdaptiveMaterial(
                            id=item.id,
                            position=item.position,
                            concept_ids=item.concept_ids,
                            competency_id=competency.id,
                        )
                    )
        return cls(
            competency_ids=tuple(item.id for item in ordered_competencies),
            concepts=tuple(concepts),
            activities=tuple(activities),
            materials=tuple(materials),
        )
