from decimal import Decimal

from shifu.learning.core.domain.entities import (
    CompetencyProgress,
    Goal,
    SkillExperience,
)
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.errors import GoalNotFoundError
from shifu.learning.core.domain.structures import (
    GoalDetail,
    GoalSkillDetail,
    GoalSkillRelation,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import CurriculumSkillOverview
from shifu.shared.core.interfaces import CurriculumContentProvider


class GetGoalDetailUseCase:
    def __init__(
        self,
        database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
    ) -> None:
        self._database = database
        self._curriculum_content_provider = curriculum_content_provider

    def execute(self, account_id: str, goal_id: str) -> GoalDetail:
        goal, experiences, progress_by_experience_id = self._read_owned_goal(
            account_id,
            goal_id,
        )
        self._validate_experiences(goal_id, experiences)
        skill_ids = tuple(experience.skill_id for experience in experiences)
        overviews = self._get_overviews(skill_ids)
        overviews_by_skill_id = self._index_overviews(skill_ids, overviews)
        skills = tuple(
            self._to_skill_detail(
                experience,
                overviews_by_skill_id[experience.skill_id],
                progress_by_experience_id.get(experience.id, ()),
            )
            for experience in experiences
        )
        ordered_skills = tuple(
            sorted(skills, key=lambda skill: (skill.name.casefold(), skill.skill_id))
        )
        included_skill_ids = frozenset(skill_ids)
        relations = self._relations(overviews, included_skill_ids)
        return GoalDetail(
            goal_id=goal.id,
            title=goal.title,
            description=goal.description,
            skills=ordered_skills,
            relations=relations,
        )

    def _read_owned_goal(
        self,
        account_id: str,
        goal_id: str,
    ) -> tuple[
        Goal,
        tuple[SkillExperience, ...],
        dict[str, tuple[CompetencyProgress, ...]],
    ]:
        with self._database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            if goal is None or goal.account_id != account_id:
                raise GoalNotFoundError
            experiences = tuple(
                repositories.skill_experiences.find_many_by_goal_id(goal_id)
            )
            progress_by_experience_id = {
                experience.id: tuple(
                    repositories.competency_progresses.find_many_by_skill_experience_id(
                        experience.id
                    )
                )
                for experience in experiences
                if experience.status is SkillExperienceStatus.LEARNING
            }
            return goal, experiences, progress_by_experience_id

    def _get_overviews(
        self,
        skill_ids: tuple[str, ...],
    ) -> tuple[CurriculumSkillOverview, ...]:
        if not skill_ids:
            return ()
        return self._curriculum_content_provider.get_skill_overviews(skill_ids)

    @staticmethod
    def _validate_experiences(
        goal_id: str,
        experiences: tuple[SkillExperience, ...],
    ) -> None:
        skill_ids: set[str] = set()
        for experience in experiences:
            if experience.goal_id != goal_id or experience.skill_id in skill_ids:
                raise ServiceUnavailableError
            skill_ids.add(experience.skill_id)

    @staticmethod
    def _index_overviews(
        skill_ids: tuple[str, ...],
        overviews: tuple[CurriculumSkillOverview, ...],
    ) -> dict[str, CurriculumSkillOverview]:
        requested_skill_ids = set(skill_ids)
        indexed: dict[str, CurriculumSkillOverview] = {}
        for overview in overviews:
            if (
                overview.skill_id not in requested_skill_ids
                or overview.skill_id in indexed
                or len(set(overview.competency_ids)) != len(overview.competency_ids)
                or len(set(overview.foundation_skill_ids))
                != len(overview.foundation_skill_ids)
            ):
                raise ServiceUnavailableError
            indexed[overview.skill_id] = overview
        if set(indexed) != requested_skill_ids:
            raise ServiceUnavailableError
        return indexed

    @classmethod
    def _to_skill_detail(
        cls,
        experience: SkillExperience,
        overview: CurriculumSkillOverview,
        progresses: tuple[CompetencyProgress, ...],
    ) -> GoalSkillDetail:
        progress = (
            cls._average_progress(experience, overview, progresses)
            if experience.status is SkillExperienceStatus.LEARNING
            else None
        )
        return GoalSkillDetail(
            skill_experience_id=experience.id,
            skill_id=experience.skill_id,
            name=overview.name,
            status=experience.status,
            progress=progress,
            inclusion_reason=experience.inclusion_reason,
        )

    @staticmethod
    def _average_progress(
        experience: SkillExperience,
        overview: CurriculumSkillOverview,
        progresses: tuple[CompetencyProgress, ...],
    ) -> Decimal:
        competency_ids = set(overview.competency_ids)
        if not competency_ids:
            raise ServiceUnavailableError
        progress_by_competency_id: dict[str, CompetencyProgress] = {}
        for progress in progresses:
            if (
                progress.skill_experience_id != experience.id
                or progress.competency_id not in competency_ids
                or progress.competency_id in progress_by_competency_id
                or progress.current_progress is None
                or not progress.current_progress.is_finite()
                or progress.current_progress < Decimal('0')
                or progress.current_progress > Decimal('100')
            ):
                raise ServiceUnavailableError
            progress_by_competency_id[progress.competency_id] = progress
        if set(progress_by_competency_id) != competency_ids:
            raise ServiceUnavailableError
        total = Decimal('0')
        for competency_id in overview.competency_ids:
            current_progress = progress_by_competency_id[competency_id].current_progress
            if current_progress is None:
                raise ServiceUnavailableError
            total += current_progress
        return total / Decimal(len(overview.competency_ids))

    @staticmethod
    def _relations(
        overviews: tuple[CurriculumSkillOverview, ...],
        included_skill_ids: frozenset[str],
    ) -> tuple[GoalSkillRelation, ...]:
        relation_pairs = {
            (foundation_skill_id, overview.skill_id)
            for overview in overviews
            for foundation_skill_id in overview.foundation_skill_ids
            if foundation_skill_id in included_skill_ids
        }
        return tuple(
            GoalSkillRelation(
                foundation_skill_id=foundation_skill_id,
                skill_id=skill_id,
            )
            for foundation_skill_id, skill_id in sorted(relation_pairs)
        )
