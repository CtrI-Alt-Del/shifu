from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from threading import Barrier
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import AiQuotaCharge
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.core.domain.structures import AiTokenCount
from shifu.intelligence.core.use_cases import RecordPlanningInferenceUsageUseCase
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.database.sqlalchemy.models import (
    AiQuotaChargeModel,
    AiQuotaMonthModel,
)
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.intelligence_fixture import MENTOR_ACCOUNT, OTHER_ACCOUNT
from tests.intelligence.core.use_cases.ai_quota_test_setup import quota_policy
from tests.intelligence.server.controllers.ai_quota_test_support import (
    CALENDAR,
    app_of,
    count_state,
    current_month,
    pin_clock,
    read_charge,
    read_month,
    seed_month,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.fixtures.intelligence_fixture import IntelligenceFixture

PATH = '/intelligence/ai-quota'
MID_NOVEMBER = datetime(2026, 11, 15, 15, 0, tzinfo=UTC)
NOVEMBER = date(2026, 11, 1)


class TestGetAiQuotaUsageController:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, mentor_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = mentor_client
        pin_clock(app_of(mentor_client), MID_NOVEMBER)

    def test_should_read_zero_and_normal_when_the_month_has_no_row(self) -> None:
        response = self.client.get(PATH)

        assert response.status_code == 200, response.text
        assert response.json() == {
            'percentage': 0,
            'status': 'normal',
            'renews_on': '2026-12-01',
        }

    def test_should_not_create_a_row_when_reading(self) -> None:
        before = count_state(self.fixture.postgres.engine)

        assert self.client.get(PATH).status_code == 200

        assert count_state(self.fixture.postgres.engine) == before
        assert read_month(self.fixture, month=NOVEMBER) is None

    @pytest.mark.parametrize(
        ('used_units', 'percentage', 'status'),
        [
            (419, 41, 'normal'),
            (799, 79, 'normal'),
            (800, 80, 'near_limit'),
            (999, 99, 'near_limit'),
            (1000, 100, 'blocked'),
            (1300, 130, 'blocked'),
        ],
    )
    def test_should_read_the_percentage_and_status_of_the_month(
        self, used_units: int, percentage: int, status: str
    ) -> None:
        seed_month(self.fixture, used_units, month=NOVEMBER)

        response = self.client.get(PATH)

        assert response.status_code == 200, response.text
        assert response.json() == {
            'percentage': percentage,
            'status': status,
            'renews_on': '2026-12-01',
        }

    def test_should_answer_with_a_private_no_store_cache_policy(self) -> None:
        response = self.client.get(PATH)

        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_expose_only_the_percentage_status_and_renewal(self) -> None:
        seed_month(self.fixture, 500, month=NOVEMBER)

        body = self.client.get(PATH).json()

        assert set(body) == {'percentage', 'status', 'renews_on'}

    def test_should_use_the_limit_copied_when_the_month_row_was_created(self) -> None:
        # The configured limit is 1000, but this month started under another one.
        seed_month(self.fixture, 1000, month=NOVEMBER, limit_units=2000)

        body = self.client.get(PATH).json()

        assert body['percentage'] == 50
        assert body['status'] == 'normal'

    def test_should_show_each_account_only_its_own_usage(self) -> None:
        seed_month(self.fixture, 410, month=NOVEMBER)
        seed_month(
            self.fixture, 1000, account_id=OTHER_ACCOUNT.account_id, month=NOVEMBER
        )

        mine = self.client.get(PATH).json()
        with self.fixture.other_account_client() as other:
            pin_clock(app_of(other), MID_NOVEMBER)
            theirs = other.get(PATH).json()

        assert mine['percentage'] == 41
        assert mine['status'] == 'normal'
        assert theirs['percentage'] == 100
        assert theirs['status'] == 'blocked'
        own = read_month(self.fixture, month=NOVEMBER)
        assert own is not None
        assert own.account_id == MENTOR_ACCOUNT.account_id

    def test_should_read_the_month_of_sao_paulo_around_the_turn_of_the_month(
        self,
    ) -> None:
        october = date(2026, 10, 1)
        seed_month(self.fixture, 900, month=october)
        seed_month(self.fixture, 100, month=NOVEMBER)

        # 2026-11-01T02:30Z is still 31 October at 23:30 in São Paulo.
        pin_clock(app_of(self.client), datetime(2026, 11, 1, 2, 30, tzinfo=UTC))
        before_midnight = self.client.get(PATH).json()
        pin_clock(app_of(self.client), datetime(2026, 11, 1, 3, 0, tzinfo=UTC))
        after_midnight = self.client.get(PATH).json()

        assert before_midnight == {
            'percentage': 90,
            'status': 'near_limit',
            'renews_on': '2026-11-01',
        }
        assert after_midnight == {
            'percentage': 10,
            'status': 'normal',
            'renews_on': '2026-12-01',
        }
        assert CALENDAR.month_of(datetime(2026, 11, 1, 2, 30, tzinfo=UTC)) == october

    def test_should_renew_in_january_after_december(self) -> None:
        pin_clock(app_of(self.client), datetime(2026, 12, 20, 15, 0, tzinfo=UTC))

        assert self.client.get(PATH).json()['renews_on'] == '2027-01-01'

    def test_should_require_a_session(self, client: TestClient) -> None:
        response = client.get(PATH)

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'


class TestAiQuotaConcurrentCharges:
    def test_should_sum_simultaneous_charges_of_one_account_without_a_lost_update(
        self, intelligence_fixture: IntelligenceFixture, mentor_client: TestClient
    ) -> None:
        workers = 8
        identifiers = SystemIdentifierProvider()
        operation_ids = [identifiers.generate() for _ in range(workers)]
        now = datetime.now(UTC)
        with intelligence_fixture.database.transaction() as repositories:
            repositories.ai_quota_months.ensure_and_lock(
                MENTOR_ACCOUNT.account_id, current_month(), 1000, now
            )
            for operation_id in operation_ids:
                repositories.ai_quota_charges.add(
                    AiQuotaCharge.create(
                        AiQuotaRequestKind.PLANNING_OPERATION,
                        operation_id,
                        MENTOR_ACCOUNT.account_id,
                        current_month(),
                        now,
                    )
                )
        barrier = Barrier(workers)

        def charge(operation_id: str) -> None:
            # Every worker opens its own transaction on its own real connection.
            database = SqlalchemyIntelligenceDatabase(
                engine=intelligence_fixture.postgres.engine
            )
            barrier.wait(timeout=30)
            RecordPlanningInferenceUsageUseCase(
                database, quota_policy(), CALENDAR, SystemClockProvider()
            ).execute(
                operation_id,
                AiTokenCount(input_tokens=10, output_tokens=5, used_tokens=15),
            )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(charge, operation_ids))

        # Each operation costs 10 + 5 * 4 = 30 units.
        month = read_month(intelligence_fixture)
        assert month is not None
        assert month.used_units == workers * 30
        for operation_id in operation_ids:
            charge_row = read_charge(
                intelligence_fixture,
                AiQuotaRequestKind.PLANNING_OPERATION,
                operation_id,
            )
            assert charge_row is not None
            assert charge_row.charged_units == 30
        assert mentor_client.get(PATH).json()['percentage'] == 24


class TestAiQuotaPersistenceConstraints:
    """The migrated schema refuses rows the domain would never write."""

    @staticmethod
    def _month(**overrides: object) -> AiQuotaMonthModel:
        values: dict[str, object] = {
            'account_id': MENTOR_ACCOUNT.account_id,
            'month': NOVEMBER,
            'used_units': 0,
            'limit_units': 1000,
            'created_at': MID_NOVEMBER,
            'updated_at': MID_NOVEMBER,
        }
        return AiQuotaMonthModel(**{**values, **overrides})

    @staticmethod
    def _charge(**overrides: object) -> AiQuotaChargeModel:
        values: dict[str, object] = {
            'request_kind': 'planning_operation',
            'request_id': '01J00000000000000000000001',
            'account_id': MENTOR_ACCOUNT.account_id,
            'month': NOVEMBER,
            'charged_units': 0,
            'refunded': False,
            'created_at': MID_NOVEMBER,
            'updated_at': MID_NOVEMBER,
        }
        return AiQuotaChargeModel(**{**values, **overrides})

    def _refuses(
        self, intelligence_fixture: IntelligenceFixture, *rows: object
    ) -> None:
        with Session(intelligence_fixture.postgres.engine) as session:
            session.add_all(rows)
            with pytest.raises(IntegrityError):
                session.commit()

    @pytest.mark.parametrize(
        'overrides',
        [
            {'used_units': -1},
            {'limit_units': 0},
            {'month': date(2026, 11, 15)},
        ],
        ids=['negative-used-units', 'non-positive-limit', 'month-not-day-one'],
    )
    def test_should_refuse_an_invalid_month_row(
        self, intelligence_fixture: IntelligenceFixture, overrides: dict[str, object]
    ) -> None:
        self._refuses(intelligence_fixture, self._month(**overrides))

        assert count_state(intelligence_fixture.postgres.engine).months == 0

    def test_should_refuse_a_duplicate_month_key(
        self, intelligence_fixture: IntelligenceFixture
    ) -> None:
        with Session(intelligence_fixture.postgres.engine) as session:
            session.add(self._month())
            session.commit()

        self._refuses(intelligence_fixture, self._month(used_units=5))

        month = read_month(intelligence_fixture, month=NOVEMBER)
        assert month is not None
        assert month.used_units == 0

    @pytest.mark.parametrize(
        'overrides',
        [{'charged_units': -1}, {'request_kind': 'title'}],
        ids=['negative-charged-units', 'unknown-request-kind'],
    )
    def test_should_refuse_an_invalid_charge_row(
        self, intelligence_fixture: IntelligenceFixture, overrides: dict[str, object]
    ) -> None:
        self._refuses(intelligence_fixture, self._charge(**overrides))

        assert count_state(intelligence_fixture.postgres.engine).charges == 0

    def test_should_refuse_a_duplicate_charge_key(
        self, intelligence_fixture: IntelligenceFixture
    ) -> None:
        with Session(intelligence_fixture.postgres.engine) as session:
            session.add(self._charge())
            session.commit()

        self._refuses(intelligence_fixture, self._charge(charged_units=7))

        assert count_state(intelligence_fixture.postgres.engine).charges == 1
