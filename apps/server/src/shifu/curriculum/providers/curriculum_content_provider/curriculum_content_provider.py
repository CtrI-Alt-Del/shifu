from shifu.curriculum.core.domain.structures import (
    ActivitySequenceItem,
    MaterialSequenceItem,
)
from shifu.curriculum.core.interfaces import CurriculumDatabase
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumContentItem,
    CurriculumMaterialContentSnapshot,
    CurriculumMaterialSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider


class DatabaseCurriculumContentProvider(CurriculumContentProvider):
    def __init__(self, database: CurriculumDatabase) -> None:
        self._database: CurriculumDatabase = database

    def get_material_content(
        self, material_id: str
    ) -> CurriculumMaterialContentSnapshot | None:
        with self._database.transaction() as repositories:
            material = repositories.materials.find_by_id(material_id)
            if material is None or material.id != material_id:
                return None

            return CurriculumMaterialContentSnapshot(
                id=material.id,
                skill_id=material.skill_id,
                title=material.title,
                material_type=material.material_type.value,
                content=material.content,
            )

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
