from dataclasses import replace

from shifu.curriculum.core.domain.structures.skill_v2_coverage import v2_coverage_gaps
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumMaterialSnapshot,
    CurriculumSkillSnapshot,
)


def _activity(
    identifier: str,
    difficulty: str,
    position: int,
    *,
    kind: str = 'learning',
    concepts: tuple[str, ...] = ('concept',),
    required: tuple[str, ...] = (),
    executable: bool = True,
) -> CurriculumActivitySnapshot:
    return CurriculumActivitySnapshot(
        id=identifier,
        title=identifier,
        activity_type=kind,
        difficulty=difficulty,
        position=position,
        concept_ids=concepts,
        required_concept_ids=required,
        question_count_by_concept=tuple((concept, 1) for concept in concepts),
        maximum_evidence_by_concept=tuple((concept, 100) for concept in concepts),
        executable_concept_evidence=executable,
    )


def _skill() -> CurriculumSkillSnapshot:
    learning = tuple(
        _activity(f'{difficulty}-{index}', difficulty, position)
        for position, (difficulty, index) in enumerate(
            (
                (difficulty, index)
                for difficulty in ('easy', 'medium', 'hard')
                for index in (1, 2)
            ),
            start=2,
        )
    )
    diagnostic = tuple(
        _activity(f'diagnostic-{difficulty}', difficulty, position, kind='diagnostic')
        for position, difficulty in enumerate(('easy', 'medium', 'hard'), start=1)
    )
    return CurriculumSkillSnapshot(
        id='skill',
        name='Skill',
        competencies=(
            CurriculumCompetencySnapshot(
                id='competency',
                skill_id='skill',
                name='Competency',
                position=1,
                items=(
                    CurriculumMaterialSnapshot(
                        id='material',
                        title='Material',
                        material_type='text',
                        position=1,
                        concept_ids=('concept',),
                    ),
                    *learning,
                ),
                concepts=(
                    CurriculumConceptSnapshot(
                        id='concept',
                        competency_id='competency',
                        name='Concept',
                        position=1,
                        prerequisite_ids=(),
                        observation_criteria='Criterion',
                    ),
                ),
                diagnostic_activities=diagnostic,
            ),
        ),
    )


def test_valid_choice_coverage_supports_all_difficulties_and_diagnostic() -> None:
    assert v2_coverage_gaps(_skill()) == ()


def test_unsupported_evaluator_cannot_be_counted_as_coverage() -> None:
    skill = _skill()
    competency = skill.competencies[0]
    items = tuple(
        replace(item, executable_concept_evidence=False)
        if isinstance(item, CurriculumActivitySnapshot) and item.id == 'hard-2'
        else item
        for item in competency.items
    )
    skill = replace(skill, competencies=(replace(competency, items=items),))

    gaps = v2_coverage_gaps(skill)
    assert 'concept:concept:hard:insufficient_learning' in gaps


def test_activity_cannot_require_its_evaluated_concept() -> None:
    skill = _skill()
    competency = skill.competencies[0]
    items = tuple(
        replace(item, required_concept_ids=('concept',))
        if isinstance(item, CurriculumActivitySnapshot) and item.id == 'easy-1'
        else item
        for item in competency.items
    )
    skill = replace(skill, competencies=(replace(competency, items=items),))
    assert 'activity:easy-1:requires_evaluated_concept' in v2_coverage_gaps(skill)


def test_activity_prerequisite_edges_participate_in_cycle_check() -> None:
    skill = _skill()
    competency = skill.competencies[0]
    another = CurriculumConceptSnapshot(
        id='another',
        competency_id='competency',
        name='Another',
        position=2,
        prerequisite_ids=('concept',),
        observation_criteria='Criterion',
    )
    items = tuple(
        replace(
            item,
            concept_ids=('concept', 'another'),
            question_count_by_concept=(('concept', 1), ('another', 1)),
            required_concept_ids=('another',),
        )
        if isinstance(item, CurriculumActivitySnapshot)
        else replace(item, concept_ids=('concept', 'another'))
        for item in competency.items
    )
    diagnostic = tuple(
        replace(
            item,
            concept_ids=('concept', 'another'),
            question_count_by_concept=(('concept', 1), ('another', 1)),
        )
        for item in competency.diagnostic_activities
    )
    skill = replace(
        skill,
        competencies=(
            replace(
                competency,
                concepts=(*competency.concepts, another),
                items=items,
                diagnostic_activities=diagnostic,
            ),
        ),
    )
    assert any(gap.endswith(':prerequisite_cycle') for gap in v2_coverage_gaps(skill))


def test_future_concept_prerequisite_blocks_v2_publication() -> None:
    skill = _skill()
    first = skill.competencies[0]
    second = CurriculumCompetencySnapshot(
        id='later',
        skill_id='skill',
        name='Later',
        position=2,
        items=(),
        concepts=(
            CurriculumConceptSnapshot(
                id='future',
                competency_id='later',
                name='Future',
                position=1,
                prerequisite_ids=(),
                observation_criteria='Criterion',
            ),
        ),
    )
    concept = replace(first.concepts[0], prerequisite_ids=('future',))
    skill = replace(skill, competencies=(replace(first, concepts=(concept,)), second))
    assert 'concept:concept:future_prerequisite:future' in v2_coverage_gaps(skill)


def test_foreign_prerequisite_blocks_v2_publication() -> None:
    skill = _skill()
    competency = skill.competencies[0]
    concept = replace(competency.concepts[0], prerequisite_ids=('unknown',))
    skill = replace(skill, competencies=(replace(competency, concepts=(concept,)),))
    assert 'concept:concept:foreign_prerequisite:unknown' in v2_coverage_gaps(skill)
