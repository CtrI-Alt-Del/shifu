from datetime import UTC, date, datetime
from unittest.mock import Mock, create_autospec

import pytest

from shifu.fakers.intelligence.entities import AiQuotaChargeFaker
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.core.domain.structures import AiTokenCount
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import RecordPlanningInferenceUsageUseCase
from shifu.shared.core.interfaces import ClockProvider

from tests.intelligence.core.use_cases.ai_quota_test_setup import (
    QUOTA_MONTH,
    AiQuotaTestSetup,
)

_NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


class TestRecordPlanningInferenceUsageUseCase(AiQuotaTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.prepare_quota(self.repositories)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = _NOW
        self.charge = AiQuotaChargeFaker.fake(
            request_kind=AiQuotaRequestKind.PLANNING_OPERATION,
            request_id='operation',
            account_id='account',
            month=QUOTA_MONTH,
        )
        self.quota_charges.find.return_value = self.charge
        self.quota_charges.find_for_update.return_value = self.charge
        self.subject = RecordPlanningInferenceUsageUseCase(
            self.database, self.quota_policy, self.quota_calendar, self.clock
        )

    def test_should_charge_the_weighted_total_to_the_month_the_request_started(
        self,
    ) -> None:
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )

        assert self.charge.charged_units == 300
        assert self.quota_month.used_units == 300
        assert self.quota_month.updated_at == _NOW
        self.quota_charges.find.assert_called_once_with(
            AiQuotaRequestKind.PLANNING_OPERATION, 'operation'
        )
        self.quota_months.lock_existing.assert_called_once_with('account', QUOTA_MONTH)
        self.quota_months.update.assert_called_once_with(self.quota_month)
        self.quota_charges.update.assert_called_once_with(self.charge)
        self.database.transaction.assert_called_once()

    def test_should_lock_the_month_before_the_charge_and_never_create_one(self) -> None:
        effects = Mock()
        effects.attach_mock(self.quota_charges.find, 'find')
        effects.attach_mock(self.quota_months.lock_existing, 'lock_month')
        effects.attach_mock(self.quota_charges.find_for_update, 'lock_charge')
        effects.attach_mock(self.quota_months.update, 'update_month')

        self.subject.execute(
            'operation', AiTokenCount(input_tokens=10, output_tokens=10, used_tokens=20)
        )

        assert [entry[0] for entry in effects.mock_calls] == [
            'find',
            'lock_month',
            'lock_charge',
            'update_month',
        ]
        self.quota_months.ensure_and_lock.assert_not_called()
        self.quota_charges.add.assert_not_called()

    def test_should_add_only_the_difference_as_the_accumulated_total_grows(
        self,
    ) -> None:
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=250, output_tokens=100, used_tokens=350),
        )

        assert self.charge.charged_units == 650
        assert self.quota_month.used_units == 650

    def test_should_keep_the_first_spend_when_an_internal_retry_restarts_the_count(
        self,
    ) -> None:
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )
        self.subject.execute(
            'operation', AiTokenCount(input_tokens=10, output_tokens=5, used_tokens=15)
        )

        assert self.charge.charged_units == 300
        assert self.quota_month.used_units == 300
        self.quota_months.update.assert_called_once()

    def test_should_not_charge_a_repeated_report_again(self) -> None:
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )

        assert self.quota_month.used_units == 300
        self.quota_months.update.assert_called_once()
        self.quota_charges.update.assert_called_once()

    def test_should_charge_the_start_month_after_the_calendar_turned(self) -> None:
        self.quota_calendar.month_of.return_value = date(2026, 11, 1)

        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )

        self.quota_months.lock_existing.assert_called_once_with('account', QUOTA_MONTH)
        self.quota_months.ensure_and_lock.assert_not_called()
        assert self.quota_month.used_units == 300

    def test_should_ignore_a_report_for_an_unknown_request(self) -> None:
        self.quota_charges.find.return_value = None

        self.subject.execute(
            'missing', AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150)
        )

        self.quota_months.lock_existing.assert_not_called()
        self.quota_months.update.assert_not_called()
        self.quota_charges.update.assert_not_called()

    def test_should_not_recreate_a_month_that_was_purged(self) -> None:
        self.quota_months.lock_existing.return_value = None

        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )

        self.quota_charges.find_for_update.assert_not_called()
        self.quota_months.ensure_and_lock.assert_not_called()
        self.quota_months.update.assert_not_called()
        assert self.charge.charged_units == 0

    def test_should_ignore_a_charge_that_vanished_before_its_lock(self) -> None:
        self.quota_charges.find_for_update.return_value = None

        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )

        self.quota_months.update.assert_not_called()
        assert self.quota_month.used_units == 0

    def test_should_ignore_reports_of_a_refunded_request(self) -> None:
        self.charge.refund(_NOW)

        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )

        assert self.charge.charged_units == 0
        assert self.quota_month.used_units == 0
        self.quota_months.update.assert_not_called()
        self.quota_charges.update.assert_not_called()

    def test_should_charge_a_total_only_report_with_the_input_weight(self) -> None:
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=None, output_tokens=None, used_tokens=120),
        )

        assert self.charge.charged_units == 120
        assert self.quota_month.used_units == 120

    def test_should_not_charge_a_report_without_counts(self) -> None:
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=None, output_tokens=None, used_tokens=None),
        )

        assert self.charge.charged_units == 0
        self.quota_months.update.assert_not_called()

    def test_should_accept_the_report_of_a_planning_that_is_over_the_limit(
        self,
    ) -> None:
        self.quota_month.used_units = 1500

        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )

        assert self.quota_month.used_units == 1800

    def test_should_charge_usage_reported_after_the_planning_was_cancelled(
        self,
    ) -> None:
        # A cancel only drops the Redis planning; the operation's charge row stays
        # and keeps accepting the usage reported while the worker finishes.
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )

        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=150, output_tokens=60, used_tokens=210),
        )

        assert self.charge.refunded is False
        assert self.charge.charged_units == 390
        assert self.quota_month.used_units == 390

    def test_should_not_charge_late_usage_of_a_refunded_operation(self) -> None:
        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=100, output_tokens=50, used_tokens=150),
        )
        self.charge.refund(_NOW)
        self.quota_month.subtract(300, _NOW)

        self.subject.execute(
            'operation',
            AiTokenCount(input_tokens=500, output_tokens=500, used_tokens=1000),
        )

        assert self.quota_month.used_units == 0
        self.quota_months.update.assert_called_once()
