from unittest.mock import Mock, create_autospec

import pytest

from shifu.intelligence.core.domain.enums import (
    AiQuotaRequestKind,
    PlanningOperationKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import (
    AiQuotaExhaustedError,
    PlanningOperationConflictError,
    PlanningSessionNotFoundError,
    PlanningStateConflictError,
)
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.domain.structures import (
    PlanningAnswer,
    PlanningOperationResult,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import RetryPlanningUseCase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider

from tests.fixtures.curriculum_planning_boundary_fixture import (
    BOUNDARY_NEXT_OPERATION_ID,
    BOUNDARY_NOW,
    boundary_answer,
    boundary_complete,
    boundary_interviewing,
    boundary_retry,
)
from tests.intelligence.core.use_cases.ai_quota_test_setup import (
    QUOTA_LIMIT,
    QUOTA_MONTH,
    AiQuotaTestSetup,
)
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCOUNT_ID,
    NEXT_OPERATION_ID,
    NOW,
    OPERATION_ID,
    OTHER_ACCOUNT_ID,
    PLANNING_ID,
    failed_session,
    interviewing_session,
)


class TestRetryPlanningUseCase(AiQuotaTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.update.return_value = True
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.prepare_quota(self.repositories, account_id=ACCOUNT_ID)
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.return_value = NEXT_OPERATION_ID
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.use_case = RetryPlanningUseCase(
            self.sessions,
            self.database,
            self.identifiers,
            self.clock,
            self.quota_policy,
            self.quota_calendar,
        )

    def test_should_rerun_a_failed_planning_over_the_preserved_context(self) -> None:
        session = failed_session()
        self.sessions.find_by_id.return_value = session

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result.status is PlanningSessionStatus.PROCESSING
        assert result.operation is not None
        assert result.operation.kind is PlanningOperationKind.RETRY
        assert result.intent == 'Quero aprender web'
        assert result.failure_code is None
        self.sessions.update.assert_called_once_with(session)
        self.repositories.events.add.assert_called_once_with(
            PlanningOperationRequestedEvent(
                payload=PlanningOperationRequestedPayload(
                    planning_id=PLANNING_ID,
                    operation_id=NEXT_OPERATION_ID,
                    generation=1,
                )
            )
        )

    def test_should_refuse_a_retry_without_a_failure(self) -> None:
        self.sessions.find_by_id.return_value = interviewing_session()

        with pytest.raises(PlanningStateConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.update.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_refuse_the_retry_that_loses_the_concurrent_write(self) -> None:
        self.sessions.find_by_id.return_value = failed_session()
        self.sessions.update.return_value = False

        with pytest.raises(PlanningOperationConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.repositories.events.add.assert_not_called()

    def test_should_hide_a_foreign_planning(self) -> None:
        self.sessions.find_by_id.return_value = failed_session(OTHER_ACCOUNT_ID)

        with pytest.raises(PlanningSessionNotFoundError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.update.assert_not_called()

    @pytest.mark.parametrize(
        'failure',
        [PlanningOperationResult.failed(), PlanningOperationResult.validation_failed()],
    )
    def test_should_preserve_answer_history_and_clear_the_failure_when_retrying(
        self, failure: PlanningOperationResult
    ) -> None:
        session = interviewing_session()
        session.submit_answers(
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
            NEXT_OPERATION_ID,
            NOW,
        )
        assert session.complete(NEXT_OPERATION_ID, 1, failure, NOW)
        self.sessions.find_by_id.return_value = session
        self.identifiers.generate.return_value = OPERATION_ID

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result.status is PlanningSessionStatus.PROCESSING
        assert result.operation is not None
        assert result.operation.kind is PlanningOperationKind.RETRY
        assert result.answered_batch_count == 1
        assert result.answered_batches[0].items[0].selected_texts == ('Sites',)
        assert result.message is None
        assert result.failure_code is None
        self.sessions.update.assert_called_once_with(result)

    def test_should_admit_the_retry_operation_before_the_planning_reaches_redis(
        self,
    ) -> None:
        self.sessions.find_by_id.return_value = failed_session()
        effects = Mock()
        effects.attach_mock(self.quota_months.ensure_and_lock, 'lock_month')
        effects.attach_mock(self.quota_charges.add, 'add_charge')
        effects.attach_mock(self.database.transaction.return_value.__exit__, 'commit')
        effects.attach_mock(self.sessions.update, 'redis_write')
        effects.attach_mock(self.repositories.events.add, 'add_event')

        self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert [entry[0] for entry in effects.mock_calls] == [
            'lock_month',
            'add_charge',
            'commit',
            'redis_write',
            'add_event',
            'commit',
        ]
        self.quota_months.ensure_and_lock.assert_called_once_with(
            ACCOUNT_ID, QUOTA_MONTH, QUOTA_LIMIT, NOW
        )
        charge = self.quota_charges.add.call_args.args[0]
        assert charge.request_kind is AiQuotaRequestKind.PLANNING_OPERATION
        assert charge.request_id == NEXT_OPERATION_ID
        assert charge.account_id == ACCOUNT_ID

    @pytest.mark.parametrize(
        'used_units', [QUOTA_LIMIT, QUOTA_LIMIT + 1, 5 * QUOTA_LIMIT]
    )
    def test_should_refuse_at_or_above_the_limit_without_any_write(
        self, used_units: int
    ) -> None:
        self.sessions.find_by_id.return_value = failed_session()
        self.quota_month.used_units = used_units

        with pytest.raises(AiQuotaExhaustedError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.update.assert_not_called()
        self.quota_charges.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_not_open_the_month_for_a_planning_that_cannot_be_retried(
        self,
    ) -> None:
        self.sessions.find_by_id.return_value = interviewing_session()

        with pytest.raises(PlanningStateConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.quota_months.ensure_and_lock.assert_not_called()


class TestRetryPlanningMigratedTransitions:
    @pytest.mark.parametrize(
        'result',
        [PlanningOperationResult.failed(), PlanningOperationResult.validation_failed()],
    )
    def test_should_retry_only_after_a_failure_and_keep_the_context(
        self, result: PlanningOperationResult
    ) -> None:
        session = boundary_interviewing()
        boundary_answer(
            session,
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
            BOUNDARY_NEXT_OPERATION_ID,
            BOUNDARY_NOW,
        )
        assert boundary_complete(
            session, BOUNDARY_NEXT_OPERATION_ID, 1, result, BOUNDARY_NOW
        )
        assert session.message is not None
        assert session.failure_code is not None
        boundary_retry(session, 'op-3', BOUNDARY_NOW)
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.operation is not None
        assert session.operation.kind is PlanningOperationKind.RETRY
        assert session.answered_batch_count == 1
        assert session.message is None
        assert session.failure_code is None

    def test_should_refuse_a_retry_without_a_failure(self) -> None:
        session = boundary_interviewing()
        with pytest.raises(PlanningStateConflictError):
            boundary_retry(session, BOUNDARY_NEXT_OPERATION_ID, BOUNDARY_NOW)
