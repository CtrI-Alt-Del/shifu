from shifu.learning.core.domain.errors import EvaluationUnavailableError
from shifu.learning.core.domain.structures import (
    ActivityRubricAssessmentDecision,
    ActivityRubricKind,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.structures import CodeRubricDecisions


class PersistActivityRubricDecisionUseCase:
    def __init__(self, learning_database: LearningDatabase) -> None:
        self._learning_database = learning_database

    def execute(
        self,
        attempt_id: str,
        run_id: str,
        question_key: str,
        rubric_kind: ActivityRubricKind,
        decisions: CodeRubricDecisions,
    ) -> None:
        with self._learning_database.transaction() as repositories:
            evaluation = (
                repositories.activity_evaluations.find_by_attempt_id_for_update(
                    attempt_id
                )
            )
            if evaluation is None:
                raise EvaluationUnavailableError

            changed = evaluation.record_rubric_decision(
                run_id,
                ActivityRubricAssessmentDecision(
                    question_key=question_key,
                    rubric_kind=rubric_kind,
                    decisions=decisions,
                ),
            )
            if changed:
                repositories.activity_evaluations.update(evaluation)
