from collections import defaultdict

from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumMaterialSnapshot,
    CurriculumSkillSnapshot,
)


def v2_coverage_gaps(skill: CurriculumSkillSnapshot) -> tuple[str, ...]:  # noqa: C901
    """Return deterministic publication gaps; legacy content remains readable."""
    gaps: list[str] = []
    concepts = {
        concept.id: (competency.position, concept)
        for competency in skill.competencies
        for concept in competency.concepts
    }
    if not concepts:
        return ('skill:no_concepts',)

    edges: dict[str, set[str]] = {concept_id: set() for concept_id in concepts}
    for concept_id, (competency_position, concept) in concepts.items():
        for prerequisite_id in concept.prerequisite_ids:
            prerequisite = concepts.get(prerequisite_id)
            if prerequisite is None:
                gaps.append(
                    f'concept:{concept_id}:foreign_prerequisite:{prerequisite_id}'
                )
            elif prerequisite[0] > competency_position:
                gaps.append(
                    f'concept:{concept_id}:future_prerequisite:{prerequisite_id}'
                )
            elif prerequisite_id == concept_id:
                gaps.append(f'concept:{concept_id}:self_prerequisite')
            else:
                edges[concept_id].add(prerequisite_id)

    for competency in skill.competencies:
        if not competency.concepts:
            gaps.append(f'competency:{competency.id}:no_concepts')
        materials = [
            item
            for item in competency.items
            if isinstance(item, CurriculumMaterialSnapshot)
        ]
        if not materials:
            gaps.append(f'competency:{competency.id}:no_material')
        for material in materials:
            if not material.concept_ids:
                gaps.append(f'material:{material.id}:no_concepts')
            for concept_id in material.concept_ids:
                if concept_id not in concepts:
                    gaps.append(f'material:{material.id}:foreign_concept:{concept_id}')

        learning = [
            item
            for item in competency.items
            if isinstance(item, CurriculumActivitySnapshot)
        ]
        diagnostic = list(competency.diagnostic_activities)
        activities = learning + diagnostic
        counts: dict[tuple[str, str], set[str]] = defaultdict(set)
        diagnostic_counts: dict[tuple[str, str], set[str]] = defaultdict(set)
        for activity in activities:
            assessed = set(activity.concept_ids)
            required = set(activity.required_concept_ids)
            if not assessed:
                gaps.append(f'activity:{activity.id}:no_concepts')
            if assessed & required:
                gaps.append(f'activity:{activity.id}:requires_evaluated_concept')
            for prerequisite_id in required:
                prerequisite = concepts.get(prerequisite_id)
                if prerequisite is None:
                    gaps.append(
                        f'activity:{activity.id}:foreign_prerequisite:{prerequisite_id}'
                    )
                elif prerequisite[0] > competency.position:
                    gaps.append(
                        f'activity:{activity.id}:future_prerequisite:{prerequisite_id}'
                    )
            for concept_id in assessed & concepts.keys():
                edges[concept_id].update(required)
            if not activity.executable_concept_evidence:
                if activity.activity_type == 'diagnostic':
                    gaps.append(f'activity:{activity.id}:no_trusted_evaluator')
                continue
            for concept_id in assessed:
                if (
                    concept_id not in concepts
                    or concepts[concept_id][1].competency_id != competency.id
                ):
                    gaps.append(
                        f'activity:{activity.id}:foreign_evaluated_concept:{concept_id}'
                    )
                    continue
                if activity.activity_type == 'diagnostic':
                    diagnostic_counts[(concept_id, activity.difficulty)].add(
                        activity.id
                    )
                else:
                    counts[(concept_id, activity.difficulty)].add(activity.id)
        for concept in competency.concepts:
            for difficulty in ('easy', 'medium', 'hard'):
                if len(counts[(concept.id, difficulty)]) < 2:
                    gaps.append(
                        f'concept:{concept.id}:{difficulty}:insufficient_learning'
                    )
                if not diagnostic_counts[(concept.id, difficulty)]:
                    gaps.append(f'concept:{concept.id}:{difficulty}:missing_diagnostic')
            hard = [
                item
                for item in learning
                if item.difficulty == 'hard'
                and concept.id in item.concept_ids
                and item.executable_concept_evidence
                and dict(item.maximum_evidence_by_concept).get(concept.id, 0) >= 80
            ]
            if not hard:
                gaps.append(f'concept:{concept.id}:no_hard_confirmation')

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(concept_id: str) -> None:
        if concept_id in visiting:
            gaps.append(f'concept:{concept_id}:prerequisite_cycle')
            return
        if concept_id in visited:
            return
        visiting.add(concept_id)
        for prerequisite_id in sorted(edges[concept_id]):
            if prerequisite_id in concepts:
                visit(prerequisite_id)
        visiting.remove(concept_id)
        visited.add(concept_id)

    for concept_id in sorted(concepts):
        visit(concept_id)
    return tuple(dict.fromkeys(gaps))
