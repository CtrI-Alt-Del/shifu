from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.interfaces import LearningDatabase


class FailCodeActivityEvaluationUseCase:
    def __init__(self, learning_database: LearningDatabase) -> None:
        self._learning_database = learning_database

    def execute(self, attempt_id: str, run_id: str) -> None:
        with self._learning_database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            if attempt is None:
                return

            if attempt.kind is ActivityAttemptKind.DIAGNOSTIC:
                experience = repositories.skill_experiences.find_by_id_for_update(
                    attempt.skill_experience_id
                )
                if (
                    experience is None
                    or experience.status is not SkillExperienceStatus.DIAGNOSING
                    or attempt.diagnostic_run_id is None
                    or experience.diagnostic_run_id != attempt.diagnostic_run_id
                ):
                    return

            evaluation = (
                repositories.activity_evaluations.find_by_attempt_id_for_update(
                    attempt_id
                )
            )
            if (
                evaluation is None
                or evaluation.status is not ActivityEvaluationStatus.PENDING
                or evaluation.run_id != run_id
            ):
                return

            evaluation.fail('evaluation_failed')
            repositories.activity_evaluations.update(evaluation)
