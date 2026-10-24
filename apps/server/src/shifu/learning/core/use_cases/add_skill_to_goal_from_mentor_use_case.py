from shifu.learning.core.domain.entities import Goal, SkillExperience
from shifu.learning.core.domain.enums import (
    MentorActionOperation,
    MentorActionOutcome,
    MentorActionRejectionReason,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import MentorActionResolution
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.mentor_action_receipt_recorder import (
    MentorActionReceiptRecorder,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumCatalogProvider,
    IdentifierProvider,
)


class AddSkillToGoalFromMentorUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_catalog_provider: CurriculumCatalogProvider,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_catalog_provider = curriculum_catalog_provider
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider
        self._recorder = MentorActionReceiptRecorder(
            identifier_provider, clock_provider
        )

    def execute(
        self,
        account_id: str,
        goal_id: str,
        confirmation_id: str,
        skill_id: str,
        justification: str,
    ) -> MentorActionResolution:
        fingerprint = self._recorder.fingerprint(
            {
                'operation': MentorActionOperation.ADD_SKILL.value,
                'goal_id': goal_id,
                'skill_id': skill_id,
                'justification': justification,
            }
        )
        with self._learning_database.transaction() as repositories:
            replayed = self._recorder.replay(
                repositories, account_id, confirmation_id, fingerprint
            )
            if replayed is not None:
                return replayed

            goal = repositories.goals.find_by_id_for_update(goal_id)

            replayed = self._recorder.replay(
                repositories, account_id, confirmation_id, fingerprint
            )
            if replayed is not None:
                return replayed

            outcome, reason, experience_id = self._apply(
                repositories, account_id, goal, goal_id, skill_id, justification
            )
            return self._recorder.record(
                repositories,
                account_id=account_id,
                confirmation_id=confirmation_id,
                operation=MentorActionOperation.ADD_SKILL,
                goal_id=goal_id,
                skill_id=skill_id,
                skill_experience_id=experience_id,
                outcome=outcome,
                rejection_reason=reason,
                fingerprint=fingerprint,
            )

    def _apply(
        self,
        repositories: LearningDatabaseRepositories,
        account_id: str,
        goal: Goal | None,
        goal_id: str,
        skill_id: str,
        justification: str,
    ) -> tuple[MentorActionOutcome, MentorActionRejectionReason | None, str | None]:
        if goal is None or goal.account_id != account_id:
            return (
                MentorActionOutcome.REJECTED,
                MentorActionRejectionReason.GOAL_UNAVAILABLE,
                None,
            )

        if self._curriculum_catalog_provider.find_skill_by_id(skill_id) is None:
            return (
                MentorActionOutcome.REJECTED,
                MentorActionRejectionReason.SKILL_UNAVAILABLE,
                None,
            )

        existing = repositories.skill_experiences.find_by_goal_id_and_skill_id(
            goal_id, skill_id
        )
        if existing is not None:
            return MentorActionOutcome.ALREADY_PRESENT, None, existing.id

        now = self._clock_provider.now()
        experience = SkillExperience.create(
            id=self._identifier_provider.generate(),
            goal_id=goal_id,
            skill_id=skill_id,
            inclusion_reason=justification,
            status=SkillExperienceStatus.NOT_STARTED,
            created_at=now,
            updated_at=now,
        )
        repositories.skill_experiences.add(experience)
        return MentorActionOutcome.ADDED, None, experience.id
