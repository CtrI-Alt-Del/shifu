from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.intelligence.entities import AiQuotaMonthFaker
from shifu.intelligence.core.domain.enums import AiQuotaStatus
from shifu.intelligence.core.domain.structures import AiQuotaUsage
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import GetAiQuotaUsageUseCase
from shifu.shared.core.interfaces import ClockProvider

from tests.intelligence.core.use_cases.ai_quota_test_setup import (
    QUOTA_LIMIT,
    QUOTA_MONTH,
    QUOTA_RENEWAL,
    AiQuotaTestSetup,
)

_NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


class TestGetAiQuotaUsageUseCase(AiQuotaTestSetup):
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
        self.subject = GetAiQuotaUsageUseCase(
            self.database, self.quota_policy, self.quota_calendar, self.clock
        )

    def test_should_report_zero_and_normal_when_the_month_has_no_record(self) -> None:
        self.quota_months.find_by_account_and_month.return_value = None

        usage = self.subject.execute('account')

        assert usage == AiQuotaUsage(
            percentage=0, status=AiQuotaStatus.NORMAL, renews_on=QUOTA_RENEWAL
        )

    @pytest.mark.parametrize(
        ('used_units', 'percentage', 'status'),
        [
            (0, 0, AiQuotaStatus.NORMAL),
            (419, 41, AiQuotaStatus.NORMAL),
            (799, 79, AiQuotaStatus.NORMAL),
            (800, 80, AiQuotaStatus.NEAR_LIMIT),
            (850, 85, AiQuotaStatus.NEAR_LIMIT),
            (999, 99, AiQuotaStatus.NEAR_LIMIT),
            (1000, 100, AiQuotaStatus.BLOCKED),
            (1001, 100, AiQuotaStatus.BLOCKED),
            (1300, 130, AiQuotaStatus.BLOCKED),
        ],
    )
    def test_should_floor_the_percentage_and_map_the_status_boundaries(
        self, used_units: int, percentage: int, status: AiQuotaStatus
    ) -> None:
        self.quota_months.find_by_account_and_month.return_value = (
            AiQuotaMonthFaker.fake(
                account_id='account',
                month=QUOTA_MONTH,
                used_units=used_units,
                limit_units=QUOTA_LIMIT,
            )
        )

        usage = self.subject.execute('account')

        assert usage.percentage == percentage
        assert usage.status is status
        assert usage.renews_on == QUOTA_RENEWAL

    def test_should_measure_against_the_limit_copied_into_the_month(self) -> None:
        self.quota_months.find_by_account_and_month.return_value = (
            AiQuotaMonthFaker.fake(
                account_id='account',
                month=QUOTA_MONTH,
                used_units=1500,
                limit_units=2000,
            )
        )

        usage = self.subject.execute('account')

        assert usage.percentage == 75
        assert usage.status is AiQuotaStatus.NORMAL

    def test_should_read_the_current_sao_paulo_month_of_the_account_only(self) -> None:
        self.subject.execute('account')

        self.quota_calendar.month_of.assert_called_once_with(_NOW)
        self.quota_calendar.renewal_of.assert_called_once_with(QUOTA_MONTH)
        self.quota_months.find_by_account_and_month.assert_called_once_with(
            'account', QUOTA_MONTH
        )

    def test_should_read_without_creating_locking_or_changing_anything(self) -> None:
        self.subject.execute('account')

        self.quota_months.ensure_and_lock.assert_not_called()
        self.quota_months.lock_existing.assert_not_called()
        self.quota_months.update.assert_not_called()
        self.quota_charges.add.assert_not_called()
        self.quota_charges.update.assert_not_called()
        self.database.transaction.assert_called_once()

    def test_should_report_the_renewal_of_the_month_that_contains_the_instant(
        self,
    ) -> None:
        self.quota_calendar.month_of.return_value = date(2026, 12, 1)
        self.quota_calendar.renewal_of.return_value = date(2027, 1, 1)

        usage = self.subject.execute('account')

        assert usage.renews_on == date(2027, 1, 1)
        self.quota_months.find_by_account_and_month.assert_called_once_with(
            'account', date(2026, 12, 1)
        )
