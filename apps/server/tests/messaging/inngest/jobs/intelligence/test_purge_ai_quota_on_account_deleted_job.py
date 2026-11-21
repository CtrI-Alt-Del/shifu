from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select

from shifu.identity.core.domain.events import AccountDeletedEvent, AccountDeletedPayload
from shifu.intelligence.core.domain.entities import AiQuotaCharge
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.core.domain.structures import AiQuotaPolicy, AiTokenCount
from shifu.intelligence.core.use_cases import RecordPlanningInferenceUsageUseCase
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.database.sqlalchemy.models import (
    AiQuotaChargeModel,
    AiQuotaMonthModel,
)
from shifu.intelligence.providers.ai_quota_calendar.zoneinfo import (
    ZoneinfoAiQuotaCalendarProvider,
)
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

_DELETED_AT = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
_MONTH = date(2026, 11, 1)
_JOB_NAME = 'intelligence.purge_ai_quota_on_account_deleted'


def _seed_quota(
    fixture: 'InngestFixture', ids: SystemIdentifierProvider, account_id: str
) -> str:
    """Persist two months and one request of the account; return the request id."""
    request_id = ids.generate()
    engine = create_engine(fixture.database_url, pool_pre_ping=True)
    try:
        database = SqlalchemyIntelligenceDatabase(engine, id_provider=ids)
        with database.transaction() as repositories:
            for month, used_units in ((date(2026, 10, 1), 900), (_MONTH, 120)):
                row = repositories.ai_quota_months.ensure_and_lock(
                    account_id, month, 1000, _DELETED_AT
                )
                row.used_units = used_units
                repositories.ai_quota_months.update(row)
            repositories.ai_quota_charges.add(
                AiQuotaCharge.create(
                    AiQuotaRequestKind.PLANNING_OPERATION,
                    request_id,
                    account_id,
                    _MONTH,
                    _DELETED_AT,
                )
            )
    finally:
        engine.dispose()
    return request_id


def _row_counts(session: 'Session', account_id: str) -> tuple[int, int]:
    months = session.scalar(
        select(func.count())
        .select_from(AiQuotaMonthModel)
        .where(AiQuotaMonthModel.account_id == account_id)
    )
    charges = session.scalar(
        select(func.count())
        .select_from(AiQuotaChargeModel)
        .where(AiQuotaChargeModel.account_id == account_id)
    )
    return months or 0, charges or 0


def _total_rows(session: 'Session') -> int:
    return sum(
        session.scalar(select(func.count()).select_from(model)) or 0
        for model in (AiQuotaMonthModel, AiQuotaChargeModel)
    )


def _publish_account_deleted(
    fixture: 'InngestFixture',
    ids: SystemIdentifierProvider,
    account_id: str,
    **extra: str,
) -> str:
    event = AccountDeletedEvent(
        payload=AccountDeletedPayload(
            account_id=account_id,
            deleted_at=_DELETED_AT.isoformat().replace('+00:00', 'Z'),
        )
    )
    event_id = ids.generate()
    fixture.publish(
        event.name,
        {
            'account_id': event.payload.account_id,
            'deleted_at': event.payload.deleted_at,
            **extra,
        },
        event_id=event_id,
    )
    return event_id


class TestPurgeAiQuotaOnAccountDeletedJob:
    def test_should_purge_only_the_deleted_accounts_quota_records(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id, other_account_id = ids.generate(), ids.generate()
        _seed_quota(inngest_fixture, ids, account_id)
        _seed_quota(inngest_fixture, ids, other_account_id)
        with inngest_fixture.inspection_session() as session:
            assert _row_counts(session, account_id) == (2, 1)

        _publish_account_deleted(inngest_fixture, ids, account_id)

        inngest_fixture.wait_for_database(
            lambda session: _row_counts(session, account_id) == (0, 0)
        )
        with inngest_fixture.inspection_session() as session:
            assert _row_counts(session, other_account_id) == (2, 1)

    def test_should_succeed_without_effect_on_duplicate_delivery(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id, other_account_id = ids.generate(), ids.generate()
        _seed_quota(inngest_fixture, ids, account_id)
        _seed_quota(inngest_fixture, ids, other_account_id)

        _publish_account_deleted(inngest_fixture, ids, account_id)
        inngest_fixture.wait_for_database(
            lambda session: _row_counts(session, account_id) == (0, 0)
        )
        _publish_account_deleted(inngest_fixture, ids, account_id)
        # Deliveries are handled in order, so the other account's purge proves the
        # duplicate for the first account completed without a failure.
        _publish_account_deleted(inngest_fixture, ids, other_account_id)
        inngest_fixture.wait_for_database(lambda session: _total_rows(session) == 0)

    def test_should_not_recreate_a_month_when_a_late_usage_report_arrives(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        request_id = _seed_quota(inngest_fixture, ids, account_id)
        _publish_account_deleted(inngest_fixture, ids, account_id)
        inngest_fixture.wait_for_database(
            lambda session: _row_counts(session, account_id) == (0, 0)
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            RecordPlanningInferenceUsageUseCase(
                SqlalchemyIntelligenceDatabase(engine, id_provider=ids),
                AiQuotaPolicy(
                    monthly_limit_units=1000,
                    input_weight=Decimal(1),
                    output_weight=Decimal(4),
                ),
                ZoneinfoAiQuotaCalendarProvider(),
                SystemClockProvider(),
            ).execute(
                request_id,
                AiTokenCount(input_tokens=100, output_tokens=10, used_tokens=110),
            )
        finally:
            engine.dispose()

        with inngest_fixture.inspection_session() as session:
            assert _row_counts(session, account_id) == (0, 0)

    def test_should_reject_invalid_payloads_as_non_retriable_without_purging(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_quota(inngest_fixture, ids, account_id)

        event_id = _publish_account_deleted(
            inngest_fixture, ids, account_id, unexpected='must be rejected'
        )

        failure_log = inngest_fixture.wait_for_log(
            f'"event":"job.failed","event_id":"{event_id}",'
            '"exception_type":"NonRetriableError",'
            f'"job":"{_JOB_NAME}"'
        )
        assert f'"job":"{_JOB_NAME}"' in failure_log
        assert '"exception_type":"NonRetriableError"' in failure_log
        with inngest_fixture.inspection_session() as session:
            assert _row_counts(session, account_id) == (2, 1)
