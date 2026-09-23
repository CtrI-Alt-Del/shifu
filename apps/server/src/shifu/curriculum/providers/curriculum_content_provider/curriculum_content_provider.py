from shifu.curriculum.core.domain.structures import (
    ActivitySequenceItem,
    MaterialSequenceItem,
    CorrectnessEvaluationPart,
    MultipleSelectionQuestion,
    SingleChoiceQuestion,
)
from decimal import Decimal
from shifu.curriculum.core.interfaces import CurriculumDatabase
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumContentItem,
    CurriculumMaterialSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider


class DatabaseCurriculumContentProvider(CurriculumContentProvider):
    def __init__(self, database: CurriculumDatabase) -> None:
        self._database: CurriculumDatabase = database

    def get_skill_content(self, skill_id: str) -> CurriculumSkillSnapshot | None:
        with self._database.transaction() as repositories:
            skill = repositories.skills.find_by_id(skill_id)
            if skill is None or skill.id != skill_id:
                return None

            competencies = repositories.competencies.find_many_by_skill_id(skill_id)
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
                            )
                        )
                        continue

                    activity = activities_by_id.get(sequence_item.activity_id)
                    if activity is None or activity.competency_id != competency.id:
                        return None
                    items.append(
                        CurriculumActivitySnapshot(
                            id=activity.id,
                            title=activity.title,
                            activity_type=activity.activity_type.value,
                            difficulty=activity.difficulty.value,
                            position=sequence_item.position,
                        )
                    )

                snapshot_competencies.append(
                    CurriculumCompetencySnapshot(
                        id=competency.id,
                        skill_id=competency.skill_id,
                        name=competency.name,
                        position=competency.position,
                        items=tuple(items),
                    )
                )

            if set(competencies_by_id) != {
                competency.id for competency in snapshot_competencies
            }:
                return None
            return CurriculumSkillSnapshot(
                id=skill.id,
                name=skill.name,
                competencies=tuple(snapshot_competencies),
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
                or activity.activity_type.value != 'learning'
                or not 3 <= len(activity.questions) <= 5
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
            )
