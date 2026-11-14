from dataclasses import dataclass
from typing import TYPE_CHECKING

from shifu.curriculum.core.domain.entities import (
    Activity,
    Competency,
    Concept,
    Material,
    Skill,
)
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ActivitySequenceItem,
    CurriculumSequence,
    MaterialSequenceItem,
)
from shifu.fakers.curriculum.entities import (
    ActivityFaker,
    CompetencyFaker,
    ConceptFaker,
    MaterialFaker,
)
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable

_DIFFICULTIES = (
    ActivityDifficulty.EASY,
    ActivityDifficulty.MEDIUM,
    ActivityDifficulty.HARD,
)
_LEARNING_ACTIVITIES_PER_DIFFICULTY = 2


@dataclass(frozen=True, slots=True)
class ReadySkillContent:
    competency: Competency
    concept: Concept
    material: Material
    activities: tuple[Activity, ...]
    curriculum_sequence: CurriculumSequence


class ReadySkillContentFaker:
    """Placeholder content that passes every Curriculum publication rule."""

    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls, *, skill: Skill, id_for: 'Callable[[int], str] | None' = None
    ) -> ReadySkillContent:
        def generate_random(_: int) -> str:
            return cls._id_provider.generate()

        generate = id_for or generate_random
        competency = CompetencyFaker.fake(
            id=generate(1),
            skill_id=skill.id,
            name=f'[Teste] Fundamentos de {skill.name}',
            description=f'Competência de teste para {skill.name}.',
            position=1,
        )
        concept = ConceptFaker.fake(
            id=generate(2),
            competency_id=competency.id,
            name=f'[Teste] Conceito de {skill.name}',
            description=f'Conceito de teste para {skill.name}.',
            position=1,
            observation_criteria='A resposta escolhe a alternativa correta.',
        )
        material = MaterialFaker.fake(
            id=generate(3),
            skill_id=skill.id,
            title=f'[Teste] Introdução a {skill.name}',
            concept_ids=(concept.id,),
        )
        # Two learning Activities per difficulty and one diagnostic each satisfy
        # the coverage rules; the hard ones confirm the Concept with full evidence.
        learning = tuple(
            ActivityFaker.fake(
                id=generate(10 + index),
                competency_id=competency.id,
                difficulty=difficulty,
                title=f'[Teste] Prática de {skill.name}',
                objective=f'Praticar {skill.name} em uma questão de teste.',
                concept_id=concept.id,
            )
            for index, difficulty in enumerate(
                difficulty
                for difficulty in _DIFFICULTIES
                for _ in range(_LEARNING_ACTIVITIES_PER_DIFFICULTY)
            )
        )
        diagnostic = tuple(
            ActivityFaker.fake(
                id=generate(20 + index),
                competency_id=competency.id,
                activity_type=ActivityType.DIAGNOSTIC,
                difficulty=difficulty,
                title=f'[Teste] Diagnóstico de {skill.name}',
                objective=f'Diagnosticar {skill.name} em uma questão de teste.',
                concept_id=concept.id,
            )
            for index, difficulty in enumerate(_DIFFICULTIES)
        )
        return ReadySkillContent(
            competency=competency,
            concept=concept,
            material=material,
            activities=(*learning, *diagnostic),
            curriculum_sequence=CurriculumSequence(
                competency_id=competency.id,
                items=(
                    MaterialSequenceItem(position=1, material_id=material.id),
                    *(
                        ActivitySequenceItem(position=position, activity_id=activity.id)
                        for position, activity in enumerate(learning, start=2)
                    ),
                ),
            ),
        )
