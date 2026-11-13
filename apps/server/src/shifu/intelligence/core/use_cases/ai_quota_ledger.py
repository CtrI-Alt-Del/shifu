import logging
from collections.abc import Sequence
from decimal import ROUND_CEILING, Decimal

from shifu.intelligence.core.domain.entities import AiQuotaCharge
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.core.domain.errors import AiQuotaExhaustedError
from shifu.intelligence.core.domain.structures import AiQuotaPolicy, AiTokenCount
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabaseRepositories,
)
from shifu.shared.core.interfaces import ClockProvider

_logger = logging.getLogger(__name__)


class AiQuotaLedger:
    """Admits, charges and refunds AI quota inside the caller's transaction.

    The ledger opens no transaction. Every consumer passes the repositories of
    the transaction that owns the change causing the quota movement, so both
    commit or roll back together. Lock order is the caller's own Mentor rows,
    then the month, then the charge.
    """

    def __init__(
        self,
        policy: AiQuotaPolicy,
        calendar: AiQuotaCalendarProvider,
        clock: ClockProvider,
    ) -> None:
        self._policy: AiQuotaPolicy = policy
        self._calendar: AiQuotaCalendarProvider = calendar
        self._clock: ClockProvider = clock

    def admit(
        self,
        repositories: IntelligenceDatabaseRepositories,
        kind: AiQuotaRequestKind,
        request_id: str,
        account_id: str,
    ) -> None:
        """Lock the month, refuse when exhausted and record the request."""
        now = self._clock.now()
        month = self._calendar.month_of(now)
        quota_month = repositories.ai_quota_months.ensure_and_lock(
            account_id, month, self._policy.monthly_limit_units, now
        )
        if quota_month.is_exhausted:
            raise AiQuotaExhaustedError
        repositories.ai_quota_charges.add(
            AiQuotaCharge.create(kind, request_id, account_id, month, now)
        )

    def assert_available(
        self,
        repositories: IntelligenceDatabaseRepositories,
        account_id: str,
    ) -> None:
        """Refuse early, without locks or rows, when the current month is exhausted.

        A cheap pre-check that spares work (such as a title call) for a start that
        admission would refuse anyway. It decides nothing: `admit` stays the
        authority, under the month lock.
        """
        month = self._calendar.month_of(self._clock.now())
        quota_month = repositories.ai_quota_months.find_by_account_and_month(
            account_id, month
        )
        if quota_month is not None and quota_month.is_exhausted:
            raise AiQuotaExhaustedError

    def register(
        self,
        repositories: IntelligenceDatabaseRepositories,
        kind: AiQuotaRequestKind,
        request_id: str,
        account_id: str,
    ) -> None:
        """Record the request without checking the limit (answers of a running planning)."""
        now = self._clock.now()
        month = self._calendar.month_of(now)
        repositories.ai_quota_months.ensure_and_lock(
            account_id, month, self._policy.monthly_limit_units, now
        )
        repositories.ai_quota_charges.add(
            AiQuotaCharge.create(kind, request_id, account_id, month, now)
        )

    def charge(
        self,
        repositories: IntelligenceDatabaseRepositories,
        kind: AiQuotaRequestKind,
        request_id: str,
        usage: Sequence[AiTokenCount],
    ) -> int:
        """Charge the positive difference between the weighted total and what was charged.

        Reads the charge without a lock, locks the month it started in, then locks
        the charge. Nothing happens when the charge or its month is gone, or when
        the charge was refunded.
        """
        found = repositories.ai_quota_charges.find(kind, request_id)
        if found is None:
            return 0
        quota_month = repositories.ai_quota_months.lock_existing(
            found.account_id, found.month
        )
        if quota_month is None:
            return 0
        charge = repositories.ai_quota_charges.find_for_update(kind, request_id)
        if charge is None or charge.refunded:
            return 0
        now = self._clock.now()
        applied = charge.charge_up_to(self._units(kind, request_id, usage), now)
        if applied == 0:
            return 0
        quota_month.add(applied, now)
        repositories.ai_quota_months.update(quota_month)
        repositories.ai_quota_charges.update(charge)
        return applied

    def refund(
        self,
        repositories: IntelligenceDatabaseRepositories,
        kind: AiQuotaRequestKind,
        request_id: str,
    ) -> int:
        """Give the charged units back to the starting month and mark the request refunded."""
        found = repositories.ai_quota_charges.find(kind, request_id)
        if found is None:
            return 0
        quota_month = repositories.ai_quota_months.lock_existing(
            found.account_id, found.month
        )
        if quota_month is None:
            return 0
        charge = repositories.ai_quota_charges.find_for_update(kind, request_id)
        if charge is None or charge.refunded:
            return 0
        now = self._clock.now()
        units = charge.refund(now)
        quota_month.subtract(units, now)
        repositories.ai_quota_months.update(quota_month)
        repositories.ai_quota_charges.update(charge)
        return units

    def _units(
        self,
        kind: AiQuotaRequestKind,
        request_id: str,
        usage: Sequence[AiTokenCount],
    ) -> int:
        total = sum(
            (self._call_units(kind, request_id, call) for call in usage),
            Decimal(0),
        )
        return int(total.to_integral_value(rounding=ROUND_CEILING))

    def _call_units(
        self, kind: AiQuotaRequestKind, request_id: str, call: AiTokenCount
    ) -> Decimal:
        if call.input_tokens is not None and call.output_tokens is not None:
            return (
                call.input_tokens * self._policy.input_weight
                + call.output_tokens * self._policy.output_weight
            )
        if call.used_tokens is not None:
            _logger.warning(
                'ai_quota_total_only_usage kind=%s request_id=%s',
                kind.value,
                request_id,
            )
            return call.used_tokens * self._policy.input_weight
        if call.input_tokens is not None or call.output_tokens is not None:
            return (call.input_tokens or 0) * self._policy.input_weight + (
                call.output_tokens or 0
            ) * self._policy.output_weight
        _logger.warning(
            'ai_quota_unknown_usage kind=%s request_id=%s', kind.value, request_id
        )
        return Decimal(0)
