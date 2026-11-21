"""Real-runtime coverage for the Communication account-deletion purge."""

import time
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, cast

from sqlalchemy import Select, create_engine, func, select
from sqlalchemy.orm import Session

from shifu.communication.core.domain.entities import (
    PushDelivery,
    StreakReminderPreference,
)
from shifu.communication.core.domain.enums import (
    PushDeliveryStatus,
    StreakReminderStatus,
)
from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
from shifu.communication.database.sqlalchemy.models import (
    PushDeliveryModel,
    PushSubscriptionModel,
    StreakReminderModel,
    StreakReminderPreferenceModel,
)
from shifu.fakers.communication.entities import (
    PushDeliveryFaker,
    PushSubscriptionFaker,
    StreakReminderFaker,
)
from shifu.identity.core.domain.events import (
    AccountDeletedEvent,
    AccountDeletedPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture

NOW = datetime(2026, 11, 18, 21, 0, tzinfo=UTC)
_FUNCTION_ID = 'communication-purge-push-data-on-account-deleted'
_RUNS_QUERY = """
    query PurgeRuns($id: ULID!) {
        eventV2(id: $id) { runs { id status function { slug } } }
    }
"""


def _seed_account(fixture: 'InngestFixture', account_id: str) -> None:
    """Give the account a subscription, a preference, a pending and a sent reminder."""

    ids = SystemIdentifierProvider()
    engine = create_engine(fixture.database_url, pool_pre_ping=True)
    try:
        database = SqlalchemyCommunicationDatabase(engine, id_provider=ids)
        with database.transaction() as repositories:
            subscription = PushSubscriptionFaker.fake(
                account_id=account_id,
                endpoint=f'https://push.example.test/send/{ids.generate()}',
            )
            repositories.push_subscriptions.add(subscription)
            repositories.streak_reminder_preferences.add(
                StreakReminderPreference.create(
                    account_id=account_id,
                    enabled=True,
                    now=NOW,
                )
            )
            pending = StreakReminderFaker.fake(
                account_id=account_id,
                local_date=date(2026, 11, 18),
                status=StreakReminderStatus.PENDING,
                attempt_count=1,
                next_attempt_at=NOW + timedelta(minutes=1),
                expires_at=NOW + timedelta(hours=6),
                created_at=NOW,
            )
            sent = StreakReminderFaker.fake(
                account_id=account_id,
                local_date=date(2026, 11, 17),
                status=StreakReminderStatus.SENT,
                attempt_count=1,
                expires_at=NOW - timedelta(hours=18),
                created_at=NOW - timedelta(days=1),
                completed_at=NOW - timedelta(days=1),
            )
            assert repositories.streak_reminders.try_add(pending)
            assert repositories.streak_reminders.try_add(sent)
            delivery: PushDelivery = PushDeliveryFaker.fake(
                reminder_id=sent.id,
                subscription_id=subscription.id,
                status=PushDeliveryStatus.SENT,
                attempted_at=NOW - timedelta(days=1),
                completed_at=NOW - timedelta(days=1),
            )
            assert repositories.push_deliveries.try_add(delivery)
    finally:
        engine.dispose()


def _counts(session: Session, account_id: str) -> dict[str, int]:
    def count(statement: Select[tuple[int]]) -> int:
        return cast('int', session.scalar(statement))

    return {
        'subscriptions': count(
            select(func.count())
            .select_from(PushSubscriptionModel)
            .where(PushSubscriptionModel.account_id == account_id)
        ),
        'preferences': count(
            select(func.count())
            .select_from(StreakReminderPreferenceModel)
            .where(StreakReminderPreferenceModel.account_id == account_id)
        ),
        'reminders': count(
            select(func.count())
            .select_from(StreakReminderModel)
            .where(StreakReminderModel.account_id == account_id)
        ),
        'deliveries': count(
            select(func.count())
            .select_from(PushDeliveryModel)
            .join(
                StreakReminderModel,
                StreakReminderModel.id == PushDeliveryModel.reminder_id,
            )
            .where(StreakReminderModel.account_id == account_id)
        ),
    }


def _pending_status(session: Session, account_id: str) -> str | None:
    return session.scalar(
        select(StreakReminderModel.status).where(
            StreakReminderModel.account_id == account_id,
            StreakReminderModel.local_date == date(2026, 11, 18),
        )
    )


def _publish_deleted(
    fixture: 'InngestFixture',
    account_id: str,
    payload: dict[str, object] | None = None,
) -> tuple[str, ...]:
    event = AccountDeletedEvent(
        payload=AccountDeletedPayload(
            account_id=account_id,
            deleted_at=NOW.isoformat().replace('+00:00', 'Z'),
        )
    )
    return fixture.publish(
        event.name,
        payload
        if payload is not None
        else {
            'account_id': event.payload.account_id,
            'deleted_at': event.payload.deleted_at,
        },
        event_id=SystemIdentifierProvider().generate(),
    )


def _run_statuses(fixture: 'InngestFixture', event_id: str) -> list[str]:
    """Statuses of this module's purge runs for the event.

    ``identity/account.deleted`` also triggers other modules' purge jobs, so
    runs are filtered by function.
    """

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
    statuses: list[str] = []
    for run in cast('list[object]', runs):
        if not isinstance(run, dict):
            continue
        run_fields = cast('dict[str, object]', run)
        function = run_fields.get('function')
        slug = (
            cast('dict[str, object]', function).get('slug')
            if isinstance(function, dict)
            else None
        )
        if isinstance(slug, str) and _FUNCTION_ID in slug:
            statuses.append(str(run_fields.get('status')))
    return statuses


def _wait_for_runs(
    fixture: 'InngestFixture',
    event_ids: tuple[str, ...],
    status: str,
    *,
    timeout: float = 90.0,
) -> None:
    deadline = time.monotonic() + timeout
    pending = list(event_ids)
    statuses: list[str] = []
    while pending and time.monotonic() < deadline:
        statuses = _run_statuses(fixture, pending[0])
        if statuses and all(value == status for value in statuses):
            pending.pop(0)
            continue
        time.sleep(0.2)
    assert not pending, (
        f'Runs did not reach {status}: {pending!r}, last statuses {statuses!r}'
    )


class TestPurgePushDataOnAccountDeletedJob:
    def test_should_purge_one_account_and_keep_the_other_intact_on_replay(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        ids = SystemIdentifierProvider()
        deleted_account_id = ids.generate()
        other_account_id = ids.generate()
        _seed_account(inngest_fixture, deleted_account_id)
        _seed_account(inngest_fixture, other_account_id)
        expected_intact = {
            'subscriptions': 1,
            'preferences': 1,
            'reminders': 2,
            'deliveries': 1,
        }
        with inngest_fixture.inspection_session() as session:
            assert _counts(session, deleted_account_id) == expected_intact

        first = _publish_deleted(inngest_fixture, deleted_account_id)

        inngest_fixture.wait_for_database(
            lambda session: (
                _counts(session, deleted_account_id)
                == dict.fromkeys(expected_intact, 0)
            )
        )
        _wait_for_runs(inngest_fixture, first, 'COMPLETED')
        with inngest_fixture.inspection_session() as session:
            assert _counts(session, other_account_id) == expected_intact
            assert _pending_status(session, other_account_id) == 'pending'

        replay = _publish_deleted(inngest_fixture, deleted_account_id)

        _wait_for_runs(inngest_fixture, replay, 'COMPLETED')
        with inngest_fixture.inspection_session() as session:
            assert _counts(session, deleted_account_id) == dict.fromkeys(
                expected_intact, 0
            )
            assert _counts(session, other_account_id) == expected_intact
            assert _pending_status(session, other_account_id) == 'pending'

    def test_should_reject_an_invalid_payload_without_deleting_anything(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed_account(inngest_fixture, account_id)

        event_ids = _publish_deleted(
            inngest_fixture,
            account_id,
            payload={
                'account_id': account_id,
                'deleted_at': NOW.isoformat().replace('+00:00', 'Z'),
                'unexpected': 'field',
            },
        )

        _wait_for_runs(inngest_fixture, event_ids, 'FAILED')
        with inngest_fixture.inspection_session() as session:
            assert _counts(session, account_id) == {
                'subscriptions': 1,
                'preferences': 1,
                'reminders': 2,
                'deliveries': 1,
            }
