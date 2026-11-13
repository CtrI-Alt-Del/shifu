from datetime import timedelta
import logging
from unittest.mock import Mock, create_autospec

import pytest

from shifu.intelligence.core.domain.enums import PlanningSessionStatus
from shifu.intelligence.core.domain.errors import PlanningSessionNotFoundError
from shifu.intelligence.core.domain.structures.planning_operation_result import (
    FAILED_MESSAGE,
    OPERATION_TIMEOUT_CODE,
)
from shifu.fakers.intelligence.entities import AiQuotaChargeFaker
from shifu.intelligence.core.domain.entities import AiQuotaCharge
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import GetPlanningSessionUseCase
from shifu.shared.core.interfaces import ClockProvider

from tests.fixtures.curriculum_planning_boundary_fixture import (
    BOUNDARY_NOW,
    boundary_expire,
    boundary_session,
)
from tests.intelligence.core.use_cases.ai_quota_test_setup import (
    AiQuotaTestSetup,
    QUOTA_MONTH,
)
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCOUNT_ID,
    NOW,
    OPERATION_ID,
    OTHER_ACCOUNT_ID,
    PLANNING_ID,
    interviewing_session,
    started_session,
)


_TIMEOUT = timedelta(minutes=3)


class TestGetPlanningSessionUseCase(AiQuotaTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.update.return_value = True
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW + timedelta(seconds=30)
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.prepare_quota(self.repositories, account_id=ACCOUNT_ID)
        self.use_case = GetPlanningSessionUseCase(
            self.sessions,
            self.clock,
            _TIMEOUT,
            self.database,
            self.quota_policy,
            self.quota_calendar,
        )

    def test_should_return_the_owner_planning_without_writing(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result is session
        assert result.status is PlanningSessionStatus.PROCESSING
        self.sessions.find_by_id.assert_called_once_with(PLANNING_ID)
        self.sessions.update.assert_not_called()

    @pytest.mark.parametrize('stored', [None, 'other-account'])
    def test_should_hide_missing_and_foreign_plannings(
        self, stored: str | None
    ) -> None:
        self.sessions.find_by_id.return_value = (
            started_session(OTHER_ACCOUNT_ID) if stored else None
        )

        with pytest.raises(PlanningSessionNotFoundError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.update.assert_not_called()

    def test_should_report_a_timed_out_operation_as_a_recoverable_failure(
        self,
    ) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session
        self.clock.now.return_value = NOW + _TIMEOUT

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result.status is PlanningSessionStatus.FAILED
        assert result.failure_code == OPERATION_TIMEOUT_CODE
        assert result.operation is None
        assert result.intent == 'Quero aprender web'
        self.sessions.update.assert_called_once_with(session)

    def test_should_expose_the_newer_state_when_the_timeout_write_loses(
        self,
    ) -> None:
        stale = started_session()
        fresh = interviewing_session()
        self.sessions.find_by_id.side_effect = [stale, fresh]
        self.sessions.update.return_value = False
        self.clock.now.return_value = NOW + _TIMEOUT

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result is fresh
        assert result.status is PlanningSessionStatus.INTERVIEW
        assert self.sessions.find_by_id.call_count == 2

    @pytest.mark.parametrize(
        'elapsed', [timedelta(minutes=2), timedelta(minutes=3), timedelta(hours=1)]
    )
    def test_should_expire_exactly_at_the_timeout_and_only_once(
        self, elapsed: timedelta
    ) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session
        self.clock.now.return_value = NOW + elapsed

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        if elapsed < _TIMEOUT:
            assert result.status is PlanningSessionStatus.PROCESSING
            self.sessions.update.assert_not_called()
        else:
            assert result.status is PlanningSessionStatus.FAILED
            assert result.failure_code == OPERATION_TIMEOUT_CODE
            assert result.message
            assert result.operation is None
            self.sessions.update.assert_called_once_with(result)
            self.sessions.update.reset_mock()
            assert self.use_case.execute(ACCOUNT_ID, PLANNING_ID) is result
            self.sessions.update.assert_not_called()

    def _wire_charge(self) -> AiQuotaCharge:
        charge = AiQuotaChargeFaker.fake(
            request_kind=AiQuotaRequestKind.PLANNING_OPERATION,
            request_id=OPERATION_ID,
            account_id=ACCOUNT_ID,
            month=QUOTA_MONTH,
            charged_units=300,
        )
        self.quota_month.used_units = 500
        self.quota_charges.find.return_value = charge
        self.quota_charges.find_for_update.return_value = charge
        return charge

    def test_should_refund_the_operation_only_after_the_expiry_is_stored(self) -> None:
        charge = self._wire_charge()
        self.sessions.find_by_id.return_value = started_session()
        self.clock.now.return_value = NOW + _TIMEOUT
        effects = Mock()
        effects.attach_mock(self.sessions.update, 'redis_write')
        effects.attach_mock(self.quota_charges.find, 'find_charge')
        effects.attach_mock(self.quota_months.lock_existing, 'lock_month')
        effects.attach_mock(self.quota_charges.find_for_update, 'lock_charge')
        effects.attach_mock(self.quota_months.update, 'update_month')

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result.status is PlanningSessionStatus.FAILED
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
        self.quota_months.lock_existing.assert_called_once_with(ACCOUNT_ID, QUOTA_MONTH)
        assert charge.refunded is True
        assert self.quota_month.used_units == 200

    def test_should_refund_to_the_start_month_when_the_expiry_is_read_later(
        self,
    ) -> None:
        self._wire_charge()
        self.sessions.find_by_id.return_value = started_session()
        self.clock.now.return_value = NOW + _TIMEOUT
        self.quota_calendar.month_of.return_value = QUOTA_MONTH.replace(month=11)

        self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.quota_months.lock_existing.assert_called_once_with(ACCOUNT_ID, QUOTA_MONTH)
        assert self.quota_month.used_units == 200

    def test_should_not_refund_when_the_planning_is_still_inside_the_timeout(
        self,
    ) -> None:
        charge = self._wire_charge()
        self.sessions.find_by_id.return_value = started_session()

        self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.database.transaction.assert_not_called()
        assert charge.refunded is False

    def test_should_keep_the_charge_when_the_expiry_write_loses(self) -> None:
        charge = self._wire_charge()
        self.sessions.find_by_id.side_effect = [
            started_session(),
            interviewing_session(),
        ]
        self.sessions.update.return_value = False
        self.clock.now.return_value = NOW + _TIMEOUT

        self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.database.transaction.assert_not_called()
        assert charge.refunded is False
        assert self.quota_month.used_units == 500

    def test_should_refund_only_once_across_repeated_reads_of_an_expired_planning(
        self,
    ) -> None:
        self._wire_charge()
        self.sessions.find_by_id.return_value = started_session()
        self.clock.now.return_value = NOW + _TIMEOUT

        self.use_case.execute(ACCOUNT_ID, PLANNING_ID)
        self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert self.quota_month.used_units == 200
        self.quota_months.update.assert_called_once()

    def test_should_return_the_expired_planning_and_log_when_the_refund_fails(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        self._wire_charge()
        session = started_session()
        self.sessions.find_by_id.return_value = session
        self.clock.now.return_value = NOW + _TIMEOUT
        self.quota_months.lock_existing.side_effect = RuntimeError('database down')

        with caplog.at_level(logging.WARNING):
            result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result is session
        assert result.status is PlanningSessionStatus.FAILED
        warnings = [r for r in caplog.records if 'ai_quota_refund_failed' in r.message]
        assert len(warnings) == 1
        assert OPERATION_ID in warnings[0].message
        assert 'database down' not in warnings[0].message


class TestGetPlanningSessionMigratedTransitions:
    def test_should_expire_only_a_processing_operation_older_than_the_timeout(
        self,
    ) -> None:
        session = boundary_session()
        timeout = timedelta(minutes=3)
        assert not boundary_expire(
            session, BOUNDARY_NOW + timedelta(minutes=2), timeout
        )
        assert session.status is PlanningSessionStatus.PROCESSING
        assert boundary_expire(session, BOUNDARY_NOW + timeout, timeout)
        assert session.status is PlanningSessionStatus.FAILED
        assert session.failure_code == OPERATION_TIMEOUT_CODE
        assert session.message == FAILED_MESSAGE
        assert session.operation is None
        assert not boundary_expire(session, BOUNDARY_NOW + timedelta(hours=1), timeout)
