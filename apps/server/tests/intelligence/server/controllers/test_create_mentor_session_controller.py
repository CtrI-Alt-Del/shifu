from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from threading import Barrier
from typing import TYPE_CHECKING

import pytest

from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from tests.intelligence.server.controllers.ai_quota_test_support import (
    EXHAUSTED_BODY,
    app_of,
    charge_attempt,
    count_state,
    pin_clock,
    read_charge,
    read_month,
    seed_month,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx2 import Response

    from tests.fixtures.intelligence_fixture import IntelligenceFixture

PATH = '/intelligence/mentor-sessions'
FIRST_KEY = '8d2b7c4e-4a1f-4c3e-9b52-6f1d3a7e9c01'
SECOND_KEY = '3f9e2a1d-7b6c-4d85-8e40-2a5c9b1f7d02'
OCTOBER = date(2026, 10, 1)
NOVEMBER = date(2026, 11, 1)


def first_message(key: str) -> dict[str, object]:
    return {'submission_key': key, 'first_message': 'Como funciona uma função?'}


class TestCreateMentorSessionController:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, mentor_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = mentor_client

    def _create(self, key: str = FIRST_KEY) -> Response:
        return self.client.post(PATH, json=first_message(key))

    def test_should_admit_the_first_message_and_record_the_request_in_the_month(
        self,
    ) -> None:
        # 15 November at 23:30 in São Paulo.
        pin_clock(app_of(self.client), datetime(2026, 11, 16, 2, 30, tzinfo=UTC))

        response = self._create()

        assert response.status_code == 201, response.text
        attempt_id = response.json()['response']['attempt_id']
        month = read_month(self.fixture, month=NOVEMBER)
        assert month is not None
        assert (month.used_units, month.limit_units) == (0, 1000)
        charge = read_charge(
            self.fixture, AiQuotaRequestKind.MENTOR_RESPONSE, attempt_id
        )
        assert charge is not None
        assert charge.month == NOVEMBER
        assert charge.charged_units == 0
        assert charge.refunded is False
        usage = self.client.get('/intelligence/ai-quota').json()
        assert usage['renews_on'] == '2026-12-01'

    def test_should_start_the_month_of_the_instant_in_sao_paulo(self) -> None:
        app = app_of(self.client)

        # 2026-11-01T02:30Z is still 31 October in São Paulo.
        pin_clock(app, datetime(2026, 11, 1, 2, 30, tzinfo=UTC))
        assert self._create(FIRST_KEY).status_code == 201
        pin_clock(app, datetime(2026, 11, 1, 3, 0, tzinfo=UTC))
        assert self._create(SECOND_KEY).status_code == 201

        assert read_month(self.fixture, month=OCTOBER) is not None
        assert read_month(self.fixture, month=NOVEMBER) is not None

    @pytest.mark.parametrize('used_units', [1000, 1300])
    def test_should_refuse_the_start_with_429_and_create_nothing(
        self, used_units: int
    ) -> None:
        pin_clock(app_of(self.client), datetime(2026, 11, 15, 15, 0, tzinfo=UTC))
        seed_month(self.fixture, used_units, month=NOVEMBER)
        before = count_state(self.fixture.postgres.engine)

        response = self._create()

        assert response.status_code == 429, response.text
        assert response.json() == EXHAUSTED_BODY
        assert count_state(self.fixture.postgres.engine) == before
        month = read_month(self.fixture, month=NOVEMBER)
        assert month is not None
        assert month.used_units == used_units
        listing = self.client.get(PATH)
        assert listing.json()['items'] == []

    def test_should_admit_the_start_just_below_the_limit(self) -> None:
        pin_clock(app_of(self.client), datetime(2026, 11, 15, 15, 0, tzinfo=UTC))
        seed_month(self.fixture, 999, month=NOVEMBER)

        response = self._create()

        assert response.status_code == 201, response.text
        month = read_month(self.fixture, month=NOVEMBER)
        assert month is not None
        assert month.used_units == 999

    def test_should_replay_an_accepted_submission_even_after_the_limit_is_reached(
        self,
    ) -> None:
        pin_clock(app_of(self.client), datetime(2026, 11, 15, 15, 0, tzinfo=UTC))
        accepted = self._create()
        assert accepted.status_code == 201
        seed_month(self.fixture, 1000, month=NOVEMBER)
        before = count_state(self.fixture.postgres.engine)

        replay = self._create()

        assert replay.status_code == 200, replay.text
        assert replay.json()['session']['id'] == accepted.json()['session']['id']
        assert count_state(self.fixture.postgres.engine) == before

    def test_should_accept_both_starts_sent_at_the_same_time_at_99_percent(
        self,
    ) -> None:
        pin_clock(app_of(self.client), datetime(2026, 11, 15, 15, 0, tzinfo=UTC))
        seed_month(self.fixture, 990, month=NOVEMBER)
        barrier = Barrier(2)

        def create(key: str) -> Response:
            barrier.wait(timeout=10)
            return self._create(key)

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(create, (FIRST_KEY, SECOND_KEY)))

        assert [response.status_code for response in responses] == [201, 201]
        attempts = [response.json()['response']['attempt_id'] for response in responses]
        assert len(set(attempts)) == 2

        # The final charges of both answers add up without a lost update.
        for attempt_id in attempts:
            self.fixture.start_processing(attempt_id)
        barrier = Barrier(2)

        def charge(attempt_id: str) -> None:
            barrier.wait(timeout=10)
            charge_attempt(self.fixture, attempt_id, input_tokens=10, output_tokens=5)

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(charge, attempts))

        month = read_month(self.fixture, month=NOVEMBER)
        assert month is not None
        # Two answers of 10 + 5 * 4 = 30 units each, on top of the 990 already used.
        assert month.used_units == 1050
        for attempt_id in attempts:
            charge_row = read_charge(
                self.fixture, AiQuotaRequestKind.MENTOR_RESPONSE, attempt_id
            )
            assert charge_row is not None
            assert charge_row.charged_units == 30

    def test_should_require_an_authenticated_learner(self, client: TestClient) -> None:
        response = client.post(PATH, json=first_message(FIRST_KEY))

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'
