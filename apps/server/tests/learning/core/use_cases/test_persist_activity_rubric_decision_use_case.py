from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.learning.core.domain.entities import ActivityEvaluation
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.errors import EvaluationUnavailableError
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import PersistActivityRubricDecisionUseCase
from shifu.shared.core.domain.structures import (
    CodeCriterionDecision,
    CodeRubricDecisions,
)

_ATTEMPT_ID = '01J000000000000000000000001'
_RUN_ID = '01J000000000000000000000002'
_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_DECISIONS = CodeRubricDecisions(
    criterion_levels=(CodeCriterionDecision(key='correctness', level=100),),
    concept_levels=(),
)


def _evaluation() -> ActivityEvaluation:
    return ActivityEvaluation.create(
        id='01J000000000000000000000003',
        attempt_id=_ATTEMPT_ID,
        status=ActivityEvaluationStatus.PENDING,
        parts=(),
        started_at=_NOW,
        run_id=_RUN_ID,
    )


class TestPersistActivityRubricDecisionUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.evaluation = _evaluation()
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = self.evaluation
        self.subject = PersistActivityRubricDecisionUseCase(self.database)

    def test_should_persist_the_decision_to_the_matching_pending_run(self) -> None:
        self.subject.execute(_ATTEMPT_ID, _RUN_ID, 'question-1', 'code', _DECISIONS)

        assert self.evaluation.rubric_decisions[0].question_key == 'question-1'
        assert self.evaluation.rubric_decisions[0].rubric_kind == 'code'
        assert self.evaluation.rubric_decisions[0].decisions == _DECISIONS
        self.repositories.activity_evaluations.update.assert_called_once_with(
            self.evaluation
        )

    def test_should_reject_a_stale_run_without_writing(self) -> None:
        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute(
                _ATTEMPT_ID, 'different-run', 'question-1', 'code', _DECISIONS
            )

        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_accept_an_identical_decision_without_duplicate_storage(
        self,
    ) -> None:
        self.subject.execute(_ATTEMPT_ID, _RUN_ID, 'question-1', 'code', _DECISIONS)
        self.repositories.activity_evaluations.update.reset_mock()

        self.subject.execute(_ATTEMPT_ID, _RUN_ID, 'question-1', 'code', _DECISIONS)

        assert len(self.evaluation.rubric_decisions) == 1
        self.repositories.activity_evaluations.update.assert_not_called()

    def test_should_reject_a_conflicting_decision_for_the_same_question(self) -> None:
        self.subject.execute(_ATTEMPT_ID, _RUN_ID, 'question-1', 'code', _DECISIONS)
        conflict = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=0),),
            concept_levels=(),
        )

        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute(_ATTEMPT_ID, _RUN_ID, 'question-1', 'code', conflict)
