from shifu.learning.core.domain.entities import Goal
from shifu.learning.core.domain.enums import (
    MentorActionOperation,
    MentorActionOutcome,
    MentorActionRejectionReason,
)
from shifu.learning.core.domain.structures import MentorActionResolution
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.mentor_action_receipt_recorder import (
    MentorActionReceiptRecorder,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class RemoveSkillExperienceFromMentorUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._learning_database = learning_database
        self._recorder = MentorActionReceiptRecorder(
            identifier_provider, clock_provider
        )

    def execute(
        self,
        account_id: str,
        goal_id: str,
        confirmation_id: str,
        skill_experience_id: str,
    ) -> MentorActionResolution:
        fingerprint = self._recorder.fingerprint(
            {
                'operation': MentorActionOperation.REMOVE_SKILL.value,
                'goal_id': goal_id,
                'skill_experience_id': skill_experience_id,
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

            outcome, reason, skill_id = self._apply(
                repositories, account_id, goal, goal_id, skill_experience_id
            )
            return self._recorder.record(
                repositories,
                account_id=account_id,
                confirmation_id=confirmation_id,
                operation=MentorActionOperation.REMOVE_SKILL,
                goal_id=goal_id,
                skill_id=skill_id,
                skill_experience_id=skill_experience_id,
                outcome=outcome,
                rejection_reason=reason,
                fingerprint=fingerprint,
            )

    @staticmethod
    def _apply(
        repositories: LearningDatabaseRepositories,
        account_id: str,
        goal: Goal | None,
        goal_id: str,
        skill_experience_id: str,
    ) -> tuple[MentorActionOutcome, MentorActionRejectionReason | None, str | None]:
        if goal is None or goal.account_id != account_id:
            return (
                MentorActionOutcome.REJECTED,
                MentorActionRejectionReason.GOAL_UNAVAILABLE,
                None,
            )

        experience = repositories.skill_experiences.find_by_id_for_update(
            skill_experience_id
        )
        if experience is None or experience.goal_id != goal_id:
            return (
                MentorActionOutcome.REJECTED,
                MentorActionRejectionReason.EXPERIENCE_UNAVAILABLE,
                None,
            )

        repositories.skill_experiences.remove(experience)
        return MentorActionOutcome.REMOVED, None, experience.skill_id
