from shifu.curriculum.core.domain.entities import (
    Activity,
    Competency,
    Concept,
    Material,
    Skill,
)
from shifu.curriculum.core.domain.structures import CurriculumSequence, SkillFoundation
from shifu.curriculum.core.interfaces import (
    ActivitiesRepository,
    CompetenciesRepository,
    ConceptsRepository,
    CurriculumSequencesRepository,
    MaterialsRepository,
    SkillFoundationsRepository,
    SkillsRepository,
)


class CurriculumSeeder:
    def __init__(
        self,
        skills_repository: SkillsRepository,
        skill_foundations_repository: SkillFoundationsRepository,
        competencies_repository: CompetenciesRepository,
        concepts_repository: ConceptsRepository,
        materials_repository: MaterialsRepository,
        activities_repository: ActivitiesRepository,
        curriculum_sequences_repository: CurriculumSequencesRepository,
    ) -> None:
        self._skills_repository = skills_repository
        self._skill_foundations_repository = skill_foundations_repository
        self._competencies_repository = competencies_repository
        self._concepts_repository = concepts_repository
        self._materials_repository = materials_repository
        self._activities_repository = activities_repository
        self._curriculum_sequences_repository = curriculum_sequences_repository

    def clear(self) -> None:
        self._curriculum_sequences_repository.remove_all()
        self._activities_repository.remove_all()
        self._materials_repository.remove_all()
        self._concepts_repository.remove_all()
        self._competencies_repository.remove_all()
        self._skill_foundations_repository.remove_all()
        self._skills_repository.remove_all()

    def run(
        self,
        skills: list[Skill],
        skill_foundations: list[SkillFoundation],
        competencies: list[Competency],
        concepts: list[Concept],
        materials: list[Material],
        activities: list[Activity],
        curriculum_sequences: list[CurriculumSequence],
    ) -> None:
        self._skills_repository.add_many(skills)
        self._skill_foundations_repository.add_many(skill_foundations)
        self._competencies_repository.add_many(competencies)
        self._concepts_repository.add_many(concepts)
        self._materials_repository.add_many(materials)
        self._activities_repository.add_many(activities)
        self._curriculum_sequences_repository.add_many(curriculum_sequences)
