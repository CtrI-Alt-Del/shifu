from shifu.learning.core.domain.structures.goal_detail import GoalDetail
from shifu.learning.core.domain.structures.goal_skill_detail import GoalSkillDetail
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.interfaces import CurriculumContentProvider


class GetGoalUseCase:
    def __init__(
        self, database: LearningDatabase, curriculum: CurriculumContentProvider
    ) -> None:
        self._database = database
        self._curriculum = curriculum

    def execute(self, account_id: str, goal_id: str) -> GoalDetail:
        with self._database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            if goal is None or goal.account_id != account_id:
                raise NotFoundError
            experiences = tuple(
                repositories.skill_experiences.find_many_by_goal_id(goal_id)
            )
        return GoalDetail(
            goal_id=goal.id,
            title=goal.title,
            description=goal.description,
            skills=tuple(
                GoalSkillDetail(
                    skill_experience_id=experience.id,
                    skill_id=experience.skill_id,
                    name=catalog.name
                    if catalog is not None
                    else 'Habilidade indisponível',
                    skill_name=catalog.name
                    if catalog is not None
                    else 'Habilidade indisponível',
                    status=experience.status,
                    progress=None,
                    inclusion_reason=experience.inclusion_reason,
                    policy_id=experience.policy_id,
                )
                for experience in experiences
                for catalog in (
                    self._curriculum.get_skill_content(experience.skill_id),
                )
            ),
            relations=(),
        )
