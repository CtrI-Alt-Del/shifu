from shifu.curriculum.core.domain.structures import (
    ActivitySequenceItem,
    MaterialSequenceItem,
    CorrectnessEvaluationPart,
    MultipleSelectionQuestion,
    SingleChoiceQuestion,
)
from decimal import Decimal
from shifu.curriculum.core.interfaces import CurriculumDatabase
from shifu.curriculum.core.domain.structures.skill_v2_coverage import v2_coverage_gaps
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumContentItem,
    CurriculumMaterialSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider


class DatabaseCurriculumContentProvider(CurriculumContentProvider):
    def __init__(self, database: CurriculumDatabase) -> None:
        self._database: CurriculumDatabase = database

    def list_skill_content(self) -> tuple[CurriculumSkillSnapshot, ...]:
        with self._database.transaction() as repositories:
            skills = tuple(
                sorted(
                    repositories.skills.find_all(),
                    key=lambda skill: (skill.name.casefold(), skill.id),
                )
            )
        return tuple(
            self.get_skill_content(skill.id)
            or CurriculumSkillSnapshot(
                id=skill.id,
                name=skill.name,
                competencies=(),
                v2_coverage_gaps=('skill:incomplete_content',),
            )
            for skill in skills
        )

    def get_skill_content(self, skill_id: str) -> CurriculumSkillSnapshot | None:  # noqa: C901
        with self._database.transaction() as repositories:
            skill = repositories.skills.find_by_id(skill_id)
            if skill is None or skill.id != skill_id:
                return None

            competencies = repositories.competencies.find_many_by_skill_id(skill_id)
            concepts = repositories.concepts.find_many_by_skill_id(skill_id)
            competencies_by_id = {
                competency.id: competency for competency in competencies
            }
            sequences = {
                competency.id: repositories.curriculum_sequences.find_by_competency_id(
                    competency.id
                )
                for competency in competencies
            }
            if any(sequence is None for sequence in sequences.values()):
                return None

            material_ids = tuple(
                item.material_id
                for sequence in sequences.values()
                if sequence is not None
                for item in sequence.items
                if isinstance(item, MaterialSequenceItem)
            )
            activity_ids = tuple(
                item.activity_id
                for sequence in sequences.values()
                if sequence is not None
                for item in sequence.items
                if isinstance(item, ActivitySequenceItem)
            )
            materials = (
                repositories.materials.find_many_by_ids(material_ids)
                if material_ids
                else []
            )
            activities = (
                repositories.activities.find_many_by_ids(activity_ids)
                if activity_ids
                else []
            )
            materials_by_id = {material.id: material for material in materials}
            activities_by_id = {activity.id: activity for activity in activities}
            diagnostic_activities = {
                competency.id: tuple(
                    sorted(
                        (
                            activity
                            for activity in repositories.activities.find_many_by_competency_id(
                                competency.id
                            )
                            if activity.activity_type.value == 'diagnostic'
                        ),
                        key=lambda activity: (
                            {'easy': 0, 'medium': 1, 'hard': 2}[
                                activity.difficulty.value
                            ],
                            activity.id,
                        ),
                    )
                )
                for competency in competencies
            }

            def activity_snapshot(
                activity: object, position: int
            ) -> CurriculumActivitySnapshot:
                from shifu.curriculum.core.domain.entities import Activity

                if not isinstance(activity, Activity):
                    raise TypeError('Expected Curriculum Activity')
                counts: dict[str, int] = {}
                possible_scores: dict[str, list[int]] = {}
                for question in activity.questions:
                    for criterion in getattr(question, 'concept_criteria', ()):
                        counts[criterion.concept_id] = (
                            counts.get(criterion.concept_id, 0) + 1
                        )
                        possible = tuple(
                            score
                            for score in (
                                criterion.correct_score,
                                criterion.incorrect_score,
                            )
                            if score is not None
                        )
                        if possible:
                            possible_scores.setdefault(criterion.concept_id, []).append(
                                max(possible)
                            )
                maximum = {
                    concept_id: sum(scores) // len(scores)
                    for concept_id, scores in possible_scores.items()
                }
                is_choice = (
                    all(
                        isinstance(
                            question, (SingleChoiceQuestion, MultipleSelectionQuestion)
                        )
                        and bool(question.concept_criteria)
                        and all(
                            criterion.correct_score is not None
                            or criterion.incorrect_score is not None
                            for criterion in question.concept_criteria
                        )
                        for question in activity.questions
                    )
                    and len(activity.evaluation_rule.parts) == len(activity.questions)
                    and bool(maximum)
                    and all(
                        isinstance(part, CorrectnessEvaluationPart)
                        for part in activity.evaluation_rule.parts
                    )
                    and {part.question_key for part in activity.evaluation_rule.parts}
                    == {question.key for question in activity.questions}
                    and (
                        activity.activity_type.value == 'diagnostic'
                        or 3 <= len(activity.questions) <= 5
                    )
                )
                return CurriculumActivitySnapshot(
                    id=activity.id,
                    title=activity.title,
                    activity_type=activity.activity_type.value,
                    difficulty=activity.difficulty.value,
                    position=position,
                    concept_ids=tuple(counts),
                    required_concept_ids=activity.required_concept_ids,
                    question_count_by_concept=tuple(sorted(counts.items())),
                    maximum_evidence_by_concept=tuple(sorted(maximum.items())),
                    executable_concept_evidence=is_choice,
                )

            snapshot_competencies: list[CurriculumCompetencySnapshot] = []
            for competency in sorted(competencies, key=lambda item: item.position):
                sequence = sequences[competency.id]
                if sequence is None:
                    return None
                items: list[CurriculumContentItem] = []
                for sequence_item in sequence.items:
                    if isinstance(sequence_item, MaterialSequenceItem):
                        material = materials_by_id.get(sequence_item.material_id)
                        if material is None or material.skill_id != skill_id:
                            return None
                        items.append(
                            CurriculumMaterialSnapshot(
                                id=material.id,
                                title=material.title,
                                material_type=material.material_type.value,
                                position=sequence_item.position,
                                concept_ids=material.concept_ids,
                                content=material.content,
                            )
                        )
                        continue

                    activity = activities_by_id.get(sequence_item.activity_id)
                    if activity is None or activity.competency_id != competency.id:
                        return None
                    items.append(activity_snapshot(activity, sequence_item.position))

                snapshot_competencies.append(
                    CurriculumCompetencySnapshot(
                        id=competency.id,
                        skill_id=competency.skill_id,
                        name=competency.name,
                        position=competency.position,
                        items=tuple(items),
                        concepts=tuple(
                            CurriculumConceptSnapshot(
                                id=concept.id,
                                competency_id=concept.competency_id,
                                name=concept.name,
                                position=concept.position,
                                prerequisite_ids=concept.prerequisite_ids,
                                observation_criteria=concept.observation_criteria,
                            )
                            for concept in concepts
                            if concept.competency_id == competency.id
                        ),
                        diagnostic_activities=tuple(
                            activity_snapshot(activity, position)
                            for position, activity in enumerate(
                                diagnostic_activities[competency.id], start=1
                            )
                        ),
                    )
                )

            if set(competencies_by_id) != {
                competency.id for competency in snapshot_competencies
            }:
                return None
            snapshot = CurriculumSkillSnapshot(
                id=skill.id,
                name=skill.name,
                competencies=tuple(snapshot_competencies),
            )
            return CurriculumSkillSnapshot(
                id=snapshot.id,
                name=snapshot.name,
                competencies=snapshot.competencies,
                v2_coverage_gaps=v2_coverage_gaps(snapshot),
            )

    def get_choice_activity(
        self,
        activity_id: str,
    ) -> CurriculumChoiceActivitySnapshot | None:
        with self._database.transaction() as repositories:
            activity = repositories.activities.find_by_id(activity_id)
            if (
                activity is None
                or activity.id != activity_id
                or (
                    activity.activity_type.value == 'learning'
                    and not 3 <= len(activity.questions) <= 5
                )
                or (
                    activity.activity_type.value == 'diagnostic'
                    and not activity.questions
                )
            ):
                return None

            questions: list[CurriculumChoiceQuestionSnapshot] = []
            keys: set[str] = set()
            for question in activity.questions:
                if not isinstance(
                    question, (SingleChoiceQuestion, MultipleSelectionQuestion)
                ):
                    return None
                if (
                    not question.correct_explanation
                    or not question.incorrect_explanation
                    or question.key in keys
                    or len({option.key for option in question.options})
                    != len(question.options)
                ):
                    return None
                keys.add(question.key)
                questions.append(
                    CurriculumChoiceQuestionSnapshot(
                        key=question.key,
                        kind=(
                            'single_choice'
                            if isinstance(question, SingleChoiceQuestion)
                            else 'multiple_selection'
                        ),
                        prompt=question.prompt,
                        options=tuple(
                            CurriculumChoiceOptionSnapshot(
                                key=option.key,
                                text=option.text,
                                is_correct=option.is_correct,
                            )
                            for option in question.options
                        ),
                        correct_explanation=question.correct_explanation,
                        incorrect_explanation=question.incorrect_explanation,
                        concept_criteria=tuple(
                            CurriculumChoiceConceptCriterionSnapshot(
                                concept_id=criterion.concept_id,
                                criterion=criterion.criterion,
                                examples=criterion.examples,
                                limits=criterion.limits,
                                correct_score=(
                                    Decimal(criterion.correct_score)
                                    if criterion.correct_score is not None
                                    else None
                                ),
                                incorrect_score=(
                                    Decimal(criterion.incorrect_score)
                                    if criterion.incorrect_score is not None
                                    else None
                                ),
                            )
                            for criterion in question.concept_criteria
                        ),
                    )
                )

            parts = tuple(
                CurriculumChoicePartSnapshot(
                    question_key=part.question_key,
                    weight_percentage=Decimal(part.weight_percentage),
                )
                for part in activity.evaluation_rule.parts
                if isinstance(part, CorrectnessEvaluationPart)
            )
            if (
                len(parts) != len(activity.evaluation_rule.parts)
                or len(parts) != len(questions)
                or {part.question_key for part in parts} != keys
            ):
                return None
            return CurriculumChoiceActivitySnapshot(
                id=activity.id,
                competency_id=activity.competency_id,
                difficulty=activity.difficulty.value,
                title=activity.title,
                questions=tuple(questions),
                parts=parts,
                required_concept_ids=activity.required_concept_ids,
                activity_type=activity.activity_type.value,
            )
