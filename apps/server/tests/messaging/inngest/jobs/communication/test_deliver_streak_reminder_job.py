"""Real-runtime coverage for the Communication streak reminder delivery job."""

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from shifu.communication.core.domain.entities import StreakReminderPreference
from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
from shifu.communication.database.sqlalchemy.models import (
    PushDeliveryModel,
    PushSubscriptionModel,
    StreakReminderModel,
)
from shifu.fakers.communication.entities import PushSubscriptionFaker
from shifu.gamification.core.domain.events import (
    StreakReminderRequestedEvent,
    StreakReminderRequestedPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.push_service_stub_fixture import (
    PushBrowserKeys,
    PushServiceStub,
)

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture

LOCAL_DATE = '2026-11-18'
STREAK_DAYS = 7
EXPECTED_BODY = 'Sua sequência de 7 dias termina hoje — pratique para mantê-la'
_RUNS_QUERY = """
    query ReminderRuns($id: ULID!) {
        eventV2(id: $id) { runs { id status } }
    }
"""


def _iso(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat().replace('+00:00', 'Z')


def _publish_requested(
    fixture: 'InngestFixture',
    account_id: str,
    *,
    expires_at: datetime,
    payload: dict[str, object] | None = None,
) -> tuple[str, ...]:
    event = StreakReminderRequestedEvent(
        payload=StreakReminderRequestedPayload(
            account_id=account_id,
            local_date=LOCAL_DATE,
            streak_days=STREAK_DAYS,
            expires_at=_iso(expires_at),
        )
    )
    return fixture.publish(
        event.name,
        payload
        if payload is not None
        else {
            'account_id': event.payload.account_id,
            'local_date': event.payload.local_date,
            'streak_days': event.payload.streak_days,
            'expires_at': event.payload.expires_at,
        },
        event_id=SystemIdentifierProvider().generate(),
    )


def _seed(
    fixture: 'InngestFixture',
    stub: PushServiceStub,
    account_id: str,
    *,
    browsers: tuple[str, ...],
    preference_enabled: bool | None = True,
) -> dict[str, PushBrowserKeys]:
    keys = {name: PushBrowserKeys.generate() for name in browsers}
    ids = SystemIdentifierProvider()
    engine = create_engine(fixture.database_url, pool_pre_ping=True)
    try:
        database = SqlalchemyCommunicationDatabase(engine, id_provider=ids)
        with database.transaction() as repositories:
            for name, browser_keys in keys.items():
                repositories.push_subscriptions.add(
                    PushSubscriptionFaker.fake(
                        account_id=account_id,
                        endpoint=stub.endpoint(name),
                        p256dh_key=browser_keys.p256dh,
                        auth_secret=browser_keys.auth,
                    )
                )
            if preference_enabled is not None:
                repositories.streak_reminder_preferences.add(
                    StreakReminderPreference.create(
                        account_id=account_id,
                        enabled=preference_enabled,
                        now=datetime.now(UTC),
                    )
                )
    finally:
        engine.dispose()
    return keys


def _reminder(session: Session, account_id: str) -> StreakReminderModel | None:
    return session.scalar(
        select(StreakReminderModel).where(StreakReminderModel.account_id == account_id)
    )


def _reminder_status(session: Session, account_id: str) -> str | None:
    reminder = _reminder(session, account_id)
    return reminder.status if reminder is not None else None


def _run_statuses(fixture: 'InngestFixture', event_id: str) -> list[str]:
    try:
        data = fixture.query_inngest(_RUNS_QUERY, {'id': event_id})
    except AssertionError:
        # The publish acknowledgment precedes asynchronous event storage, so
        # the event is unknown to the Dev Server for a moment.
        return []
    observed = data.get('eventV2')
    if not isinstance(observed, dict):
        return []
    runs: object = cast('dict[str, object]', observed).get('runs')
    if not isinstance(runs, list):
        return []
    return [
        str(cast('dict[str, object]', run).get('status'))
        for run in cast('list[object]', runs)
        if isinstance(run, dict)
    ]


def _wait_for_runs(
    fixture: 'InngestFixture',
    event_ids: tuple[str, ...],
    status: str,
    *,
    timeout: float = 120.0,
) -> None:
    deadline = time.monotonic() + timeout
    pending = list(event_ids)
    while pending and time.monotonic() < deadline:
        statuses = _run_statuses(fixture, pending[0])
        if statuses and all(value == status for value in statuses):
            pending.pop(0)
            continue
        time.sleep(0.2)
    assert not pending, f'Runs did not reach {status}: {pending!r}'


class TestDeliverStreakReminderJob:
    def test_should_deliver_exactly_one_encrypted_push_per_subscription(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        keys = _seed(
            inngest_fixture, push_service_stub, account_id, browsers=('one', 'two')
        )
        expires_at = datetime.now(UTC) + timedelta(hours=2)

        event_ids = _publish_requested(
            inngest_fixture, account_id, expires_at=expires_at
        )

        inngest_fixture.wait_for_database(
            lambda session: _reminder_status(session, account_id) == 'sent'
        )
        _wait_for_runs(inngest_fixture, event_ids, 'COMPLETED')
        for name, browser_keys in keys.items():
            received = push_service_stub.requests(name)
            assert len(received) == 1
            request = received[0]
            assert request.content_encoding == 'aes128gcm'
            assert request.has_vapid_authorization is True
            assert request.ttl is not None
            assert 7000 <= int(request.ttl) <= 7200
            assert EXPECTED_BODY.encode() not in request.body
            assert browser_keys.decrypt(request.body) == {
                'title': 'Shifu',
                'body': EXPECTED_BODY,
                'url': '/',
                'tag': 'shifu-streak-reminder',
            }
        with inngest_fixture.inspection_session() as session:
            reminder = _reminder(session, account_id)
            assert reminder is not None
            assert reminder.status == 'sent'
            assert reminder.attempt_count == 1
            assert reminder.next_attempt_at is None
            assert reminder.completed_at is not None
            deliveries = session.scalars(select(PushDeliveryModel)).all()
            assert [delivery.status for delivery in deliveries] == ['sent', 'sent']

    def test_should_add_nothing_for_a_duplicate_event_or_a_replay(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(inngest_fixture, push_service_stub, account_id, browsers=('one', 'two'))
        expires_at = datetime.now(UTC) + timedelta(hours=2)
        first = _publish_requested(inngest_fixture, account_id, expires_at=expires_at)
        duplicate = _publish_requested(
            inngest_fixture, account_id, expires_at=expires_at
        )
        inngest_fixture.wait_for_database(
            lambda session: _reminder_status(session, account_id) == 'sent'
        )
        _wait_for_runs(inngest_fixture, (*first, *duplicate), 'COMPLETED')

        replay = _publish_requested(inngest_fixture, account_id, expires_at=expires_at)
        _wait_for_runs(inngest_fixture, replay, 'COMPLETED')

        assert len(push_service_stub.requests('one')) == 1
        assert len(push_service_stub.requests('two')) == 1
        with inngest_fixture.inspection_session() as session:
            reminders = session.scalars(select(StreakReminderModel)).all()
            assert len(reminders) == 1
            assert reminders[0].status == 'sent'
            assert reminders[0].attempt_count == 1
            assert len(session.scalars(select(PushDeliveryModel)).all()) == 2

    def test_should_remove_gone_browsers_while_the_others_still_receive(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(
            inngest_fixture,
            push_service_stub,
            account_id,
            browsers=('gone', 'missing', 'active'),
        )
        push_service_stub.program('gone', 410)
        push_service_stub.program('missing', 404)

        _publish_requested(
            inngest_fixture,
            account_id,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )

        inngest_fixture.wait_for_database(
            lambda session: _reminder_status(session, account_id) == 'sent'
        )
        assert len(push_service_stub.requests('gone')) == 1
        assert len(push_service_stub.requests('missing')) == 1
        assert len(push_service_stub.requests('active')) == 1
        with inngest_fixture.inspection_session() as session:
            remaining = session.scalars(select(PushSubscriptionModel.endpoint)).all()
            assert remaining == [push_service_stub.endpoint('active')]
            outcomes = sorted(
                (delivery.status, delivery.failure_code)
                for delivery in session.scalars(select(PushDeliveryModel)).all()
            )
            assert outcomes == [
                ('failed', 'subscription_gone'),
                ('failed', 'subscription_gone'),
                ('sent', None),
            ]

    def test_should_retry_a_temporary_failure_once_after_the_scheduled_delay(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(inngest_fixture, push_service_stub, account_id, browsers=('flaky',))
        push_service_stub.program('flaky', 500, 201)

        _publish_requested(
            inngest_fixture,
            account_id,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )

        # The first retry waits the production one-minute delay.
        received = push_service_stub.wait_for_requests('flaky', 2, timeout=150)
        inngest_fixture.wait_for_database(
            lambda session: _reminder_status(session, account_id) == 'sent',
            timeout=60,
        )
        assert len(push_service_stub.requests('flaky')) == 2
        assert received[1].received_at - received[0].received_at >= 55
        with inngest_fixture.inspection_session() as session:
            reminder = _reminder(session, account_id)
            assert reminder is not None
            assert reminder.attempt_count == 2
            deliveries = session.scalars(select(PushDeliveryModel)).all()
            assert [delivery.status for delivery in deliveries] == ['sent']

    def test_should_send_once_to_accepted_and_retry_only_the_temporary_browser(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(
            inngest_fixture,
            push_service_stub,
            account_id,
            browsers=('accepted', 'gone', 'flaky'),
        )
        push_service_stub.program('accepted', 201)
        push_service_stub.program('gone', 410)
        push_service_stub.program('flaky', 500, 201)

        event_ids = _publish_requested(
            inngest_fixture,
            account_id,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )

        # The flaky browser is retried after the production one-minute delay.
        push_service_stub.wait_for_requests('flaky', 2, timeout=150)
        inngest_fixture.wait_for_database(
            lambda session: _reminder_status(session, account_id) == 'sent',
            timeout=60,
        )
        _wait_for_runs(inngest_fixture, event_ids, 'COMPLETED')
        assert len(push_service_stub.requests('accepted')) == 1
        assert len(push_service_stub.requests('gone')) == 1
        assert len(push_service_stub.requests('flaky')) == 2
        with inngest_fixture.inspection_session() as session:
            remaining = sorted(
                session.scalars(select(PushSubscriptionModel.endpoint)).all()
            )
            assert remaining == sorted(
                [
                    push_service_stub.endpoint('accepted'),
                    push_service_stub.endpoint('flaky'),
                ]
            )
            reminder = _reminder(session, account_id)
            assert reminder is not None
            assert reminder.status == 'sent'
            assert reminder.attempt_count == 2
            outcomes = sorted(
                (delivery.status, delivery.failure_code)
                for delivery in session.scalars(select(PushDeliveryModel)).all()
            )
            assert outcomes == [
                ('failed', 'subscription_gone'),
                ('sent', None),
                ('sent', None),
            ]

    def test_should_not_retry_a_permanent_failure(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(inngest_fixture, push_service_stub, account_id, browsers=('rejected',))
        push_service_stub.program('rejected', 400)

        event_ids = _publish_requested(
            inngest_fixture,
            account_id,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )

        inngest_fixture.wait_for_database(
            lambda session: _reminder_status(session, account_id) == 'failed'
        )
        _wait_for_runs(inngest_fixture, event_ids, 'COMPLETED')
        assert len(push_service_stub.requests('rejected')) == 1
        with inngest_fixture.inspection_session() as session:
            reminder = _reminder(session, account_id)
            assert reminder is not None
            assert reminder.status == 'failed'
            assert reminder.attempt_count == 1
            assert reminder.next_attempt_at is None
            deliveries = session.scalars(select(PushDeliveryModel)).all()
            assert [(d.status, d.failure_code) for d in deliveries] == [
                ('failed', 'http_400')
            ]
            assert len(session.scalars(select(PushSubscriptionModel)).all()) == 1

    def test_should_not_follow_a_redirect_from_a_push_service(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(inngest_fixture, push_service_stub, account_id, browsers=('redirecting',))
        push_service_stub.program('redirecting', 302)

        event_ids = _publish_requested(
            inngest_fixture,
            account_id,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )

        inngest_fixture.wait_for_database(
            lambda session: _reminder_status(session, account_id) == 'failed'
        )
        _wait_for_runs(inngest_fixture, event_ids, 'COMPLETED')
        assert len(push_service_stub.requests('redirecting')) == 1
        assert push_service_stub.requests(PushServiceStub.REDIRECT_TARGET) == []
        with inngest_fixture.inspection_session() as session:
            deliveries = session.scalars(select(PushDeliveryModel)).all()
            assert [(d.status, d.failure_code) for d in deliveries] == [
                ('failed', 'http_302')
            ]

    def test_should_expire_without_a_later_request_when_no_retry_fits(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(inngest_fixture, push_service_stub, account_id, browsers=('limited',))
        push_service_stub.program('limited', 429)
        expires_at = datetime.now(UTC) + timedelta(seconds=25)

        event_ids = _publish_requested(
            inngest_fixture, account_id, expires_at=expires_at
        )

        inngest_fixture.wait_for_database(
            lambda session: _reminder_status(session, account_id) == 'expired'
        )
        _wait_for_runs(inngest_fixture, event_ids, 'COMPLETED')
        requests = push_service_stub.requests('limited')
        assert len(requests) == 1
        assert requests[0].received_at < expires_at.timestamp()
        with inngest_fixture.inspection_session() as session:
            reminder = _reminder(session, account_id)
            assert reminder is not None
            assert reminder.status == 'expired'
            assert reminder.next_attempt_at is None
            assert session.scalars(select(PushDeliveryModel)).all() == []

    @pytest.mark.parametrize(
        ('preference_enabled', 'browsers'),
        [(False, ('quiet',)), (None, ('quiet',)), (True, ())],
        ids=['preference-off', 'preference-never-set', 'no-subscription'],
    )
    def test_should_skip_without_any_request(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
        preference_enabled: bool | None,
        browsers: tuple[str, ...],
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(
            inngest_fixture,
            push_service_stub,
            account_id,
            browsers=browsers,
            preference_enabled=preference_enabled,
        )

        event_ids = _publish_requested(
            inngest_fixture,
            account_id,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )

        inngest_fixture.wait_for_database(
            lambda session: _reminder_status(session, account_id) == 'skipped'
        )
        _wait_for_runs(inngest_fixture, event_ids, 'COMPLETED')
        assert push_service_stub.requests() == []
        with inngest_fixture.inspection_session() as session:
            assert session.scalars(select(PushDeliveryModel)).all() == []

    def test_should_reject_an_invalid_payload_without_any_effect(
        self,
        inngest_fixture: 'InngestFixture',
        push_service_stub: PushServiceStub,
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(inngest_fixture, push_service_stub, account_id, browsers=('one',))

        event_ids = _publish_requested(
            inngest_fixture,
            account_id,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
            payload={
                'account_id': account_id,
                'local_date': LOCAL_DATE,
                'streak_days': 0,
                'expires_at': _iso(datetime.now(UTC) + timedelta(hours=2)),
                'unexpected': 'field',
            },
        )

        _wait_for_runs(inngest_fixture, event_ids, 'FAILED')
        assert push_service_stub.requests() == []
        with inngest_fixture.inspection_session() as session:
            assert session.scalars(select(StreakReminderModel)).all() == []
