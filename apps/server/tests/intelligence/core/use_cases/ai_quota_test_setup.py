"""Quota doubles shared by the use-case tests that consume the AI quota ledger.

The ledger has no test module of its own; every consumer proves its scenarios on
these autospecced ports, a policy given as data and a controlled calendar.
"""

from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import Mock, create_autospec

from shifu.fakers.intelligence.entities import AiQuotaMonthFaker
from shifu.intelligence.core.domain.entities import AiQuotaMonth
from shifu.intelligence.core.domain.structures import AiQuotaPolicy
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    AiQuotaChargesRepository,
    AiQuotaMonthsRepository,
)

QUOTA_LIMIT = 1000
QUOTA_MONTH = date(2026, 10, 1)
QUOTA_RENEWAL = date(2026, 11, 1)


def quota_policy() -> AiQuotaPolicy:
    """The test configuration: limit 1000, input weight 1 and output weight 4."""
    return AiQuotaPolicy(
        monthly_limit_units=QUOTA_LIMIT,
        input_weight=Decimal(1),
        output_weight=Decimal(4),
    )


def quota_calendar(month: date = QUOTA_MONTH) -> Mock:
    calendar = create_autospec(AiQuotaCalendarProvider, instance=True)
    calendar.month_of.return_value = month
    calendar.renewal_of.return_value = QUOTA_RENEWAL
    return calendar


class AiQuotaTestSetup:
    quota_policy: AiQuotaPolicy
    quota_calendar: Mock
    quota_months: Mock
    quota_charges: Mock
    quota_month: AiQuotaMonth

    def prepare_quota(
        self,
        repositories: Any,
        *,
        account_id: str = 'account',
        month: date = QUOTA_MONTH,
        used_units: int = 0,
    ) -> None:
        """Wire the quota ports into `repositories` with a month below the limit."""
        self.quota_policy = quota_policy()
        self.quota_calendar = quota_calendar(month)
        self.quota_months = create_autospec(AiQuotaMonthsRepository, instance=True)
        self.quota_charges = create_autospec(AiQuotaChargesRepository, instance=True)
        self.quota_month = AiQuotaMonthFaker.fake(
            account_id=account_id,
            month=month,
            used_units=used_units,
            limit_units=QUOTA_LIMIT,
        )
        self.quota_months.ensure_and_lock.return_value = self.quota_month
        self.quota_months.lock_existing.return_value = self.quota_month
        self.quota_months.find_by_account_and_month.return_value = self.quota_month
        self.quota_charges.find.return_value = None
        self.quota_charges.find_for_update.return_value = None
        repositories.ai_quota_months = self.quota_months
        repositories.ai_quota_charges = self.quota_charges
