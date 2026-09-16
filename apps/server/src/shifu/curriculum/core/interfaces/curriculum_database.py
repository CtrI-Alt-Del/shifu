from contextlib import AbstractContextManager
from typing import Protocol

from shifu.curriculum.core.interfaces.activities_repository import (
    ActivitiesRepository,
)
from shifu.curriculum.core.interfaces.competencies_repository import (
    CompetenciesRepository,
)
from shifu.curriculum.core.interfaces.curriculum_sequences_repository import (
    CurriculumSequencesRepository,
)
from shifu.curriculum.core.interfaces.materials_repository import MaterialsRepository
from shifu.curriculum.core.interfaces.skill_foundations_repository import (
    SkillFoundationsRepository,
)
from shifu.curriculum.core.interfaces.skills_repository import SkillsRepository
from shifu.shared.core.domain.structures import structure


@structure
class CurriculumDatabaseRepositories:
    skills: SkillsRepository
    skill_foundations: SkillFoundationsRepository
    competencies: CompetenciesRepository
    materials: MaterialsRepository
    activities: ActivitiesRepository
    curriculum_sequences: CurriculumSequencesRepository


class CurriculumDatabase(Protocol):
    def transaction(
        self,
    ) -> AbstractContextManager[CurriculumDatabaseRepositories]:
        """Open the sole transaction boundary for one Curriculum operation."""
        ...
