"""Helpers shared by the controller tests that touch the monthly AI quota.

They seed and read the quota rows through the real repositories on the disposable
PostgreSQL database and pin the application clock through the composition seam, so
the assertions never depend on the wall clock or on shared data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, cast
from unittest.mock import create_autospec

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.structures import MentorInferenceUsage
from shifu.intelligence.core.use_cases import (
    FailMentorResponseUseCase,
    RecordMentorInferenceUsageUseCase,
)
from shifu.intelligence.database.sqlalchemy.models import (
    AiQuotaChargeModel,
    AiQuotaMonthModel,
    MentorMessageModel,
    MentorResponseAttemptModel,
    MentorSessionModel,
)
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.providers.ai_quota_calendar.zoneinfo import (
    ZoneinfoAiQuotaCalendarProvider,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
from tests.fixtures.intelligence_fixture import MENTOR_ACCOUNT
from tests.intelligence.core.use_cases.ai_quota_test_setup import (
    QUOTA_LIMIT,
    quota_policy,
)

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import Engine

    from shifu.intelligence.core.domain.entities import AiQuotaCharge, AiQuotaMonth
    from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
    from tests.fixtures.intelligence_fixture import IntelligenceFixture

EXHAUSTED_BODY = {
    'code': 'ai_quota_exhausted',
    'message': (
        'Sua cota mensal de IA acabou. '
        'O Mentor e o planejamento assistido voltam na renovação.'
    ),
}
CALENDAR = ZoneinfoAiQuotaCalendarProvider()


def current_month() -> date:
    """The quota month of the wall clock, for tests that keep the real clock."""
    return CALENDAR.month_of(datetime.now(UTC))


def pin_clock(app: FastAPI, instant: datetime) -> None:
    """Make every request of the application see ``instant`` as the current time."""
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = instant
    app.dependency_overrides[IntelligencePipe.get_clock_provider] = lambda: clock


def app_of(client: TestClient) -> FastAPI:
    return cast('FastAPI', client.app)


def seed_month(
    fixture: IntelligenceFixture,
    used_units: int,
    *,
    account_id: str = MENTOR_ACCOUNT.account_id,
    month: date | None = None,
    limit_units: int = QUOTA_LIMIT,
) -> None:
    """Create the account's month row with ``used_units`` already spent."""
    target = month or current_month()
    now = datetime.now(UTC)
    with fixture.database.transaction() as repositories:
        row = repositories.ai_quota_months.ensure_and_lock(
            account_id, target, limit_units, now
        )
        row.used_units = used_units
        repositories.ai_quota_months.update(row)


def read_month(
    fixture: IntelligenceFixture,
    *,
    account_id: str = MENTOR_ACCOUNT.account_id,
    month: date | None = None,
) -> AiQuotaMonth | None:
    with fixture.database.transaction() as repositories:
        return repositories.ai_quota_months.find_by_account_and_month(
            account_id, month or current_month()
        )


def read_charge(
    fixture: IntelligenceFixture, kind: AiQuotaRequestKind, request_id: str
) -> AiQuotaCharge | None:
    with fixture.database.transaction() as repositories:
        return repositories.ai_quota_charges.find(kind, request_id)


@dataclass(frozen=True)
class StateCounts:
    """Row counts of everything a refused start must leave untouched."""

    sessions: int
    messages: int
    attempts: int
    events: int
    charges: int
    months: int


def count_state(engine: Engine) -> StateCounts:
    def count(model: type[object]) -> int:
        return session.scalar(select(func.count()).select_from(model)) or 0

    with Session(engine) as session:
        return StateCounts(
            sessions=count(MentorSessionModel),
            messages=count(MentorMessageModel),
            attempts=count(MentorResponseAttemptModel),
            events=count(EventModel),
            charges=count(AiQuotaChargeModel),
            months=count(AiQuotaMonthModel),
        )


def charge_attempt(
    fixture: IntelligenceFixture,
    attempt_id: str,
    *,
    input_tokens: int,
    output_tokens: int,
    call_key: str = 'generated-0:writer:0',
) -> None:
    """Report one inference of the claimed attempt, as the answer workflow does."""
    access = create_autospec(MentorAccessProvider, instance=True)
    access.authorize.side_effect = _grant
    RecordMentorInferenceUsageUseCase(
        fixture.database,
        _wall_clock(),
        access,
        quota_policy(),
        CALENDAR,
    ).execute(
        attempt_id,
        'test-owner',
        MentorInferenceUsage(
            call_key=call_key,
            profile='writer',
            used_tokens=input_tokens + output_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
    )


def fail_attempt(fixture: IntelligenceFixture, attempt_id: str) -> None:
    """Fail the claimed attempt through the real use case, which refunds its charge."""
    access = create_autospec(MentorAccessProvider, instance=True)
    FailMentorResponseUseCase(
        fixture.database,
        _wall_clock(),
        access,
        quota_policy(),
        CALENDAR,
    ).execute(attempt_id, 'test-owner', 'service_unavailable')


def _grant(account_id: str, operation_key: str) -> MentorAccessGrant:
    return MentorAccessGrant(
        account_id=account_id,
        access_revision='controlled-test-revision',
        operation_key=operation_key,
    )


def _wall_clock() -> ClockProvider:
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.side_effect = lambda: datetime.now(UTC)
    return clock
