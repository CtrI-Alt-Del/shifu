from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.learning.core.domain.errors import CurriculumGapError
from shifu.learning.core.domain.entities import (
    CompetencyProgress,
    Goal,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)


class CreateGoalUseCase:
    def __init__(
        self,
        database: LearningDatabase,
        curriculum: CurriculumContentProvider,
        clock: ClockProvider,
        identifiers: IdentifierProvider,
    ) -> None:
        self._database = database
        self._curriculum = curriculum
        self._clock = clock
        self._identifiers = identifiers

    def execute(
        self,
        account_id: str,
        title: str,
        description: str,
        skill_ids: tuple[str, ...] = (),
    ) -> Goal:
        title = title.strip()
        description = description.strip()
        if not title or not description or len(set(skill_ids)) != len(skill_ids):
            raise ValidationError
        catalogs = tuple(
            self._curriculum.get_skill_content(skill_id) for skill_id in skill_ids
        )
        if any(
            catalog is None or catalog.id != skill_id or not catalog.v2_eligible
            for skill_id, catalog in zip(skill_ids, catalogs, strict=True)
        ):
            raise CurriculumGapError
        now = self._clock.now()
        goal = Goal(
            id=self._identifiers.generate(),
            account_id=account_id,
            title=title,
            description=description,
            created_at=now,
            updated_at=now,
        )
        with self._database.transaction() as repositories:
            repositories.goals.add_many([goal])
            for skill_id, catalog in zip(skill_ids, catalogs, strict=True):
                if catalog is None:
                    raise ValidationError
                experience = SkillExperience.create(
                    id=self._identifiers.generate(),
                    goal_id=goal.id,
                    skill_id=skill_id,
                    inclusion_reason=None,
                    status=SkillExperienceStatus.NOT_STARTED,
                    created_at=now,
                    updated_at=now,
                    policy_id=AdaptiveLearningPolicy.policy_id,
                )
                repositories.skill_experiences.add_many([experience])
                repositories.competency_progresses.add_many(
                    [
                        CompetencyProgress(
                            id=self._identifiers.generate(),
                            skill_experience_id=experience.id,
                            competency_id=competency.id,
                            content_released=False,
                            created_at=now,
                            updated_at=now,
                            status=CompetencyProgressStatus.LEARNING,
                        )
                        for competency in catalog.competencies
                    ]
                )
        return goal
