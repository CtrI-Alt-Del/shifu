from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.domain.structures import CurriculumMaterialSnapshot
from shifu.shared.core.interfaces import CurriculumContentProvider


class GetMaterialUseCase:
    def __init__(
        self, database: LearningDatabase, curriculum: CurriculumContentProvider
    ) -> None:
        self._database = database
        self._curriculum = curriculum

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        material_id: str,
    ) -> CurriculumMaterialSnapshot:
        with self._database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if goal is None or goal.account_id != account_id or experience is None:
                raise NotFoundError
            progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
                experience.id, competency_id
            )
            if progress is None or not progress.content_released:
                raise NotFoundError
        catalog = self._curriculum.get_skill_content(skill_id)
        if catalog is None:
            raise NotFoundError
        competency = next(
            (item for item in catalog.competencies if item.id == competency_id), None
        )
        if competency is None:
            raise NotFoundError
        material = next(
            (
                item
                for item in competency.items
                if isinstance(item, CurriculumMaterialSnapshot)
                and item.id == material_id
            ),
            None,
        )
        if material is None:
            raise NotFoundError
        return material
