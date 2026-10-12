from shifu.curriculum.core.domain.enums import ActivityType
from shifu.curriculum.core.domain.structures import MaterialSequenceItem
from shifu.curriculum.core.interfaces import (
    CurriculumDatabase,
    CurriculumDatabaseRepositories,
)
from shifu.shared.core.domain.structures import MentorCatalogEntry


class CurriculumMentorCatalogProvider:
    """Project only non-personal search fields; Learning supplies eligibility."""

    def __init__(self, database: CurriculumDatabase) -> None:
        self._database = database

    def read_projection(self) -> tuple[MentorCatalogEntry, ...]:
        entries: list[MentorCatalogEntry] = []
        with self._database.transaction() as repositories:
            for skill in repositories.skills.find_all():
                entries.append(
                    MentorCatalogEntry(
                        reference_id=skill.id,
                        kind='skill',
                        skill_id=skill.id,
                        competency_id=None,
                        title=skill.name,
                        description=skill.description,
                        concept_ids=(),
                        source_version='curriculum-projection-v1',
                    )
                )
                for competency in repositories.competencies.find_many_by_skill_id(
                    skill.id
                ):
                    entries.append(
                        MentorCatalogEntry(
                            reference_id=competency.id,
                            kind='competency',
                            skill_id=skill.id,
                            competency_id=competency.id,
                            title=competency.name,
                            description=competency.description,
                            concept_ids=(),
                            source_version='curriculum-projection-v1',
                        )
                    )
                    entries.extend(
                        self._content_entries(repositories, skill.id, competency.id)
                    )
        return tuple(entries)

    @staticmethod
    def _content_entries(
        repositories: CurriculumDatabaseRepositories,
        skill_id: str,
        competency_id: str,
    ) -> list[MentorCatalogEntry]:
        entries: list[MentorCatalogEntry] = []
        sequence = repositories.curriculum_sequences.find_by_competency_id(
            competency_id
        )
        if sequence is not None:
            for item in sequence.items:
                if not isinstance(item, MaterialSequenceItem):
                    continue
                material = repositories.materials.find_by_id(item.material_id)
                if material is not None and material.skill_id == skill_id:
                    entries.append(
                        MentorCatalogEntry(
                            reference_id=material.id,
                            kind='material',
                            skill_id=skill_id,
                            competency_id=competency_id,
                            title=material.title,
                            description=None,
                            concept_ids=material.concept_ids,
                            source_version='curriculum-projection-v1',
                        )
                    )
        for activity in repositories.activities.find_learning_by_competency_id(
            competency_id
        ):
            if activity.activity_type is ActivityType.LEARNING:
                entries.append(
                    MentorCatalogEntry(
                        reference_id=activity.id,
                        kind='activity',
                        skill_id=skill_id,
                        competency_id=competency_id,
                        title=activity.title,
                        description=activity.objective,
                        concept_ids=activity.required_concept_ids,
                        source_version='curriculum-projection-v1',
                    )
                )
        return entries

    def is_diagnostic_activity(
        self,
        skill_id: str,
        competency_id: str | None,
        activity_id: str,
    ) -> bool:
        with self._database.transaction() as repositories:
            return any(
                (competency_id is None or competency.id == competency_id)
                and repositories.activities.has_diagnostic_activity(
                    competency.id, activity_id
                )
                for competency in repositories.competencies.find_many_by_skill_id(
                    skill_id
                )
            )

    def search(
        self,
        account_id: str,
        query: str,
        eligible_references: tuple[str, ...],
    ) -> tuple[MentorCatalogEntry, ...]:
        eligible = frozenset(eligible_references)
        terms = tuple(query.casefold().split())
        return tuple(
            entry
            for entry in self.read_projection()
            if entry.reference_id in eligible
            and terms
            and any(
                term in f'{entry.title} {entry.description or ""}'.casefold()
                for term in terms
            )
        )
