import hashlib
import json

from shifu.learning.core.domain.entities import (
    CompetencyProgress,
    Goal,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.errors import (
    CurriculumGapError,
    GoalConfirmationConflictError,
    InvalidGoalError,
)
from shifu.learning.core.domain.structures import GoalConfirmation
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.structures import (
    CurriculumSkillSnapshot,
    PlannedGoalConfirmation,
    PlannedGoalCreation,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)

MAX_TITLE_LENGTH = 240
MAX_DESCRIPTION_LENGTH = 4000
MAX_INCLUSION_REASON_LENGTH = 2000


class CreatePlannedGoalUseCase:
    """Turn a confirmed Planner proposal into a Goal once per confirmation key.

    Learning validates its own rules again, creates the Goal, every Skill
    experience with its inclusion rationale and the competency progresses as one
    transaction, and records the confirmation so a repeat returns the same Goal.
    """

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

    def execute(self, confirmation: PlannedGoalConfirmation) -> PlannedGoalCreation:
        title = confirmation.title.strip()
        description = confirmation.description.strip()
        skills = tuple(
            (skill.skill_id, skill.inclusion_reason.strip())
            for skill in confirmation.skills
        )
        _validate(title, description, skills)
        fingerprint = _fingerprint(title, description, skills)

        with self._database.transaction() as repositories:
            repositories.goal_confirmations.lock(
                confirmation.account_id, confirmation.confirmation_key
            )
            existing = repositories.goal_confirmations.find(
                confirmation.account_id, confirmation.confirmation_key
            )
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise GoalConfirmationConflictError
                return PlannedGoalCreation(
                    goal_id=existing.goal_id,
                    confirmation_key=existing.confirmation_key,
                    replayed=True,
                )

            catalogs = self._eligible_catalogs(skills)
            now = self._clock.now()
            goal = Goal(
                id=self._identifiers.generate(),
                account_id=confirmation.account_id,
                title=title,
                description=description,
                created_at=now,
                updated_at=now,
            )
            repositories.goals.add_many([goal])
            for (skill_id, inclusion_reason), catalog in zip(
                skills, catalogs, strict=True
            ):
                experience = SkillExperience.create(
                    id=self._identifiers.generate(),
                    goal_id=goal.id,
                    skill_id=skill_id,
                    inclusion_reason=inclusion_reason,
                    status=SkillExperienceStatus.NOT_STARTED,
                    created_at=now,
                    updated_at=now,
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
            repositories.goal_confirmations.add(
                GoalConfirmation(
                    account_id=confirmation.account_id,
                    confirmation_key=confirmation.confirmation_key,
                    planning_id=confirmation.planning_id,
                    goal_id=goal.id,
                    fingerprint=fingerprint,
                    created_at=now,
                )
            )
        return PlannedGoalCreation(
            goal_id=goal.id,
            confirmation_key=confirmation.confirmation_key,
            replayed=False,
        )

    def _eligible_catalogs(
        self, skills: tuple[tuple[str, str], ...]
    ) -> tuple[CurriculumSkillSnapshot, ...]:
        catalogs: list[CurriculumSkillSnapshot] = []
        for skill_id, _ in skills:
            catalog = self._curriculum.get_skill_content(skill_id)
            if catalog is None or catalog.id != skill_id or not catalog.v2_eligible:
                raise CurriculumGapError
            catalogs.append(catalog)
        return tuple(catalogs)


def _validate(
    title: str, description: str, skills: tuple[tuple[str, str], ...]
) -> None:
    skill_ids = [skill_id for skill_id, _ in skills]
    if (
        not title
        or len(title) > MAX_TITLE_LENGTH
        or not description
        or len(description) > MAX_DESCRIPTION_LENGTH
        or not skills
        or len(set(skill_ids)) != len(skill_ids)
        or any(
            not reason or len(reason) > MAX_INCLUSION_REASON_LENGTH
            for _, reason in skills
        )
    ):
        raise InvalidGoalError


def _fingerprint(
    title: str, description: str, skills: tuple[tuple[str, str], ...]
) -> str:
    payload = json.dumps(
        {'title': title, 'description': description, 'skills': list(skills)},
        ensure_ascii=False,
        separators=(',', ':'),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()
