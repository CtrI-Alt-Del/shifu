import logging
from unittest.mock import Mock, create_autospec

import pytest

from shifu.intelligence.core.domain.enums import (
    PlanningIntentKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.structures import PlanningOperationResult
from shifu.intelligence.core.domain.structures.planning_operation_result import (
    VALIDATION_EXHAUSTED_CODE,
)
from shifu.fakers.intelligence.entities import AiQuotaChargeFaker
from shifu.intelligence.core.domain.entities import AiQuotaCharge
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import CompletePlanningOperationUseCase
from shifu.shared.core.interfaces import ClockProvider

from tests.fixtures.curriculum_planning_boundary_fixture import (
    BOUNDARY_NEXT_OPERATION_ID,
    BOUNDARY_NOW,
    BOUNDARY_OPERATION_ID,
    boundary_batch,
    boundary_complete,
    boundary_proposal,
    boundary_session,
)
from tests.intelligence.core.use_cases.ai_quota_test_setup import (
    AiQuotaTestSetup,
    QUOTA_MONTH,
)
from tests.intelligence.core.use_cases.planning_test_setup import (
    NEXT_OPERATION_ID,
    NOW,
    OPERATION_ID,
    PLANNING_ID,
    batch,
    proposal,
    started_session,
)


class TestCompletePlanningOperationUseCase(AiQuotaTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.update.return_value = True
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.prepare_quota(self.repositories, account_id='account')
        self.use_case = CompletePlanningOperationUseCase(
            self.sessions,
            self.clock,
            self.database,
            self.quota_policy,
            self.quota_calendar,
        )
        self.result = PlanningOperationResult.for_batch(
            batch(), classification=PlanningIntentKind.AMBIGUOUS
        )

    def test_should_apply_the_result_of_the_current_operation(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        applied = self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, self.result)

        assert applied is True
        assert session.status is PlanningSessionStatus.INTERVIEW
        assert session.batch is not None
        assert session.classification is PlanningIntentKind.AMBIGUOUS
        assert session.consulted_curriculum is True
        assert session.operation is None
        self.sessions.update.assert_called_once_with(session)

    def test_should_drop_a_result_for_a_planning_that_was_cancelled(self) -> None:
        self.sessions.find_by_id.return_value = None

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, self.result) is False
        self.sessions.update.assert_not_called()

    def test_should_drop_a_result_of_a_superseded_operation(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        assert (
            self.use_case.execute(PLANNING_ID, NEXT_OPERATION_ID, 1, self.result)
            is False
        )
        assert session.status is PlanningSessionStatus.PROCESSING
        self.sessions.update.assert_not_called()

    def test_should_drop_a_result_that_loses_the_concurrent_write(self) -> None:
        self.sessions.find_by_id.return_value = started_session()
        self.sessions.update.return_value = False

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, self.result) is False

    def test_should_drop_a_result_from_an_old_generation(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 2, self.result) is False

        assert session.status is PlanningSessionStatus.PROCESSING
        self.sessions.update.assert_not_called()

    def test_should_never_apply_the_same_operation_twice(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session
        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, self.result)
        self.sessions.update.reset_mock()

        assert not self.use_case.execute(
            PLANNING_ID,
            OPERATION_ID,
            1,
            PlanningOperationResult.for_proposal(proposal()),
        )

        assert session.status is PlanningSessionStatus.INTERVIEW
        self.sessions.update.assert_not_called()

    @pytest.mark.parametrize(
        ('result', 'status', 'failure_code'),
        [
            (
                PlanningOperationResult.out_of_scope(
                    classification=PlanningIntentKind.OUT_OF_SCOPE
                ),
                PlanningSessionStatus.OUT_OF_SCOPE,
                None,
            ),
            (
                PlanningOperationResult.unsupported(),
                PlanningSessionStatus.UNSUPPORTED,
                None,
            ),
            (
                PlanningOperationResult.validation_failed(),
                PlanningSessionStatus.VALIDATION_FAILED,
                'validation_exhausted',
            ),
            (
                PlanningOperationResult.failed(),
                PlanningSessionStatus.FAILED,
                'service_unavailable',
            ),
        ],
    )
    def test_should_expose_distinct_terminal_results_and_clear_private_operation_state(
        self,
        result: PlanningOperationResult,
        status: PlanningSessionStatus,
        failure_code: str | None,
    ) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, result)

        assert session.status is status
        assert session.message
        assert session.failure_code == failure_code
        assert session.operation is None
        assert session.batch is None
        assert session.proposal is None
        self.sessions.update.assert_called_once_with(session)

    def _wire_charge(self) -> AiQuotaCharge:
        charge = AiQuotaChargeFaker.fake(
            request_kind=AiQuotaRequestKind.PLANNING_OPERATION,
            request_id=OPERATION_ID,
            account_id='account',
            month=QUOTA_MONTH,
            charged_units=300,
        )
        self.quota_month.used_units = 500
        self.quota_charges.find.return_value = charge
        self.quota_charges.find_for_update.return_value = charge
        return charge

    @pytest.mark.parametrize(
        'result',
        [PlanningOperationResult.failed(), PlanningOperationResult.validation_failed()],
        ids=['failed', 'validation_failed'],
    )
    def test_should_refund_only_after_the_redis_write_is_accepted(
        self, result: PlanningOperationResult
    ) -> None:
        charge = self._wire_charge()
        self.sessions.find_by_id.return_value = started_session()
        effects = Mock()
        effects.attach_mock(self.sessions.update, 'redis_write')
        effects.attach_mock(self.quota_charges.find, 'find_charge')
        effects.attach_mock(self.quota_months.lock_existing, 'lock_month')
        effects.attach_mock(self.quota_charges.find_for_update, 'lock_charge')
        effects.attach_mock(self.quota_months.update, 'update_month')

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, result) is True

        assert [entry[0] for entry in effects.mock_calls] == [
            'redis_write',
            'find_charge',
            'lock_month',
            'lock_charge',
            'update_month',
        ]
        self.quota_charges.find.assert_called_once_with(
            AiQuotaRequestKind.PLANNING_OPERATION, OPERATION_ID
        )
        self.quota_months.lock_existing.assert_called_once_with('account', QUOTA_MONTH)
        assert charge.refunded is True
        assert self.quota_month.used_units == 200

    def test_should_refund_to_the_start_month_after_the_calendar_turned(self) -> None:
        self._wire_charge()
        self.quota_calendar.month_of.return_value = QUOTA_MONTH.replace(month=11)
        self.sessions.find_by_id.return_value = started_session()

        self.use_case.execute(
            PLANNING_ID, OPERATION_ID, 1, PlanningOperationResult.failed()
        )

        self.quota_months.lock_existing.assert_called_once_with('account', QUOTA_MONTH)
        assert self.quota_month.used_units == 200

    @pytest.mark.parametrize(
        'result',
        [
            PlanningOperationResult.for_batch(batch()),
            PlanningOperationResult.for_proposal(proposal()),
            PlanningOperationResult.out_of_scope(),
            PlanningOperationResult.unsupported(),
        ],
        ids=['batch', 'proposal', 'out_of_scope', 'unsupported'],
    )
    def test_should_keep_the_charge_of_a_result_that_is_not_a_failure(
        self, result: PlanningOperationResult
    ) -> None:
        charge = self._wire_charge()
        self.sessions.find_by_id.return_value = started_session()

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, result) is True

        self.database.transaction.assert_not_called()
        assert charge.refunded is False
        assert self.quota_month.used_units == 500

    def test_should_keep_the_charge_when_the_failed_result_loses_the_redis_write(
        self,
    ) -> None:
        charge = self._wire_charge()
        self.sessions.find_by_id.return_value = started_session()
        self.sessions.update.return_value = False

        assert not self.use_case.execute(
            PLANNING_ID, OPERATION_ID, 1, PlanningOperationResult.failed()
        )

        self.database.transaction.assert_not_called()
        assert charge.refunded is False
        assert self.quota_month.used_units == 500

    def test_should_keep_the_charge_of_a_cancelled_planning(self) -> None:
        charge = self._wire_charge()
        self.sessions.find_by_id.return_value = None

        assert not self.use_case.execute(
            PLANNING_ID, OPERATION_ID, 1, PlanningOperationResult.failed()
        )

        self.database.transaction.assert_not_called()
        assert charge.refunded is False

    def test_should_keep_the_charge_when_the_failed_result_is_stale(self) -> None:
        charge = self._wire_charge()
        self.sessions.find_by_id.return_value = started_session()

        assert not self.use_case.execute(
            PLANNING_ID, NEXT_OPERATION_ID, 1, PlanningOperationResult.failed()
        )

        self.database.transaction.assert_not_called()
        assert charge.refunded is False

    def test_should_refund_once_when_the_failed_result_is_delivered_twice(
        self,
    ) -> None:
        self._wire_charge()
        self.sessions.find_by_id.return_value = started_session()
        failed = PlanningOperationResult.failed()

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, failed)
        assert not self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, failed)

        assert self.quota_month.used_units == 200
        self.quota_months.update.assert_called_once()

    def test_should_keep_the_stored_result_and_log_when_the_refund_fails(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._wire_charge()
        session = started_session()
        self.sessions.find_by_id.return_value = session
        self.quota_months.lock_existing.side_effect = RuntimeError('database down')

        with caplog.at_level(logging.WARNING):
            applied = self.use_case.execute(
                PLANNING_ID, OPERATION_ID, 1, PlanningOperationResult.failed()
            )

        assert applied is True
        assert session.status is PlanningSessionStatus.FAILED
        self.sessions.update.assert_called_once_with(session)
        warnings = [r for r in caplog.records if 'ai_quota_refund_failed' in r.message]
        assert len(warnings) == 1
        assert OPERATION_ID in warnings[0].message
        assert 'database down' not in warnings[0].message


class TestCompletePlanningOperationMigratedTransitions:
    @pytest.mark.parametrize(
        ('operation_id', 'generation'),
        [(BOUNDARY_NEXT_OPERATION_ID, 1), (BOUNDARY_OPERATION_ID, 2)],
    )
    def test_should_discard_results_that_miss_the_operation_or_generation_fence(
        self, operation_id: str, generation: int
    ) -> None:
        session = boundary_session()
        assert not boundary_complete(
            session,
            operation_id,
            generation,
            PlanningOperationResult.for_batch(boundary_batch()),
            BOUNDARY_NOW,
        )
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.operation is not None

    def test_should_discard_a_second_result_for_the_same_operation(self) -> None:
        session = boundary_session()
        assert boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_batch(boundary_batch()),
            BOUNDARY_NOW,
        )
        assert not boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_proposal(boundary_proposal()),
            BOUNDARY_NOW,
        )
        assert session.status is PlanningSessionStatus.INTERVIEW

    @pytest.mark.parametrize(
        ('result', 'status', 'failure_code'),
        [
            (
                PlanningOperationResult.out_of_scope(
                    classification=PlanningIntentKind.OUT_OF_SCOPE
                ),
                PlanningSessionStatus.OUT_OF_SCOPE,
                None,
            ),
            (
                PlanningOperationResult.unsupported(),
                PlanningSessionStatus.UNSUPPORTED,
                None,
            ),
            (
                PlanningOperationResult.validation_failed(),
                PlanningSessionStatus.VALIDATION_FAILED,
                VALIDATION_EXHAUSTED_CODE,
            ),
            (
                PlanningOperationResult.failed(),
                PlanningSessionStatus.FAILED,
                'service_unavailable',
            ),
        ],
    )
    def test_should_expose_distinguishable_outcomes_with_a_learner_message(
        self,
        result: PlanningOperationResult,
        status: PlanningSessionStatus,
        failure_code: str | None,
    ) -> None:
        session = boundary_session()
        assert boundary_complete(
            session, BOUNDARY_OPERATION_ID, 1, result, BOUNDARY_NOW
        )
        assert session.status is status
        assert session.message
        assert session.failure_code == failure_code
        assert session.operation is None
        assert session.batch is None
        assert session.proposal is None
