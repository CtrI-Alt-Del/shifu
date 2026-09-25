"""Real-runtime coverage for scheduled expiry fan-out and child isolation."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shifu.identity.core.domain.events import (
    AccountExpiryRequestedEvent,
    AccountExpiryRequestedPayload,
)
from shifu.identity.database.sqlalchemy.models import AccountModel
from shifu.shared.database.sqlalchemy.models import EventModel

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


_FUNCTION_ID = 'shifu-identity-fan-out-unconfirmed-account-expiry'
_RUNTIME_BATCH_SIZE = 5
_ACCOUNT_EXPIRY_REQUESTED_EVENT_NAME = AccountExpiryRequestedEvent(
    payload=AccountExpiryRequestedPayload(account_id='test')
).name


class TestFanOutUnconfirmedAccountExpiryJob:
    def test_cron_fans_out_bounded_independent_children_and_is_idempotent(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        _insert_expired_pending_accounts(inngest_fixture, count=_RUNTIME_BATCH_SIZE + 1)

        inngest_fixture.invoke_function(_FUNCTION_ID)
        inngest_fixture.wait_for_database(
            lambda session: (
                _count_accounts_with_status(session, 'deleted')
                == _RUNTIME_BATCH_SIZE + 1
            ),
            timeout=300.0,
        )

        with inngest_fixture.inspection_session() as session:
            assert _count_accounts_with_status(session, 'pending-confirmation') == 0
            assert _count_expiry_requested_events(session) == _RUNTIME_BATCH_SIZE + 1

        inngest_fixture.invoke_function(_FUNCTION_ID)
        inngest_fixture.wait_for_database(
            lambda session: (
                _count_accounts_with_status(session, 'deleted')
                == _RUNTIME_BATCH_SIZE + 1
            ),
        )

        with inngest_fixture.inspection_session() as session:
            assert _count_expiry_requested_events(session) == _RUNTIME_BATCH_SIZE + 1
            accounts = session.scalars(select(AccountModel)).all()
            assert len(accounts) == _RUNTIME_BATCH_SIZE + 1
            assert all(account.access_version == 2 for account in accounts)

        inngest_fixture.invoke_function(_FUNCTION_ID)
        inngest_fixture.wait_for_database(
            lambda session: (
                _count_expiry_requested_events(session) == _RUNTIME_BATCH_SIZE + 1
            )
        )

        with inngest_fixture.inspection_session() as session:
            assert (
                _count_accounts_with_status(session, 'deleted')
                == _RUNTIME_BATCH_SIZE + 1
            )
            assert _count_expiry_requested_events(session) == _RUNTIME_BATCH_SIZE + 1


def _insert_expired_pending_accounts(
    fixture: 'InngestFixture',
    *,
    count: int,
) -> None:
    now = datetime.now(UTC)
    expired_at = now - timedelta(days=8)
    with fixture.inspection_session() as session:
        session.add_all(
            [
                AccountModel(
                    id=f'01JEXPIRY{index:017d}',
                    display_name=f'Expiry learner {index}',
                    email=f'expiry-{index}@example.com',
                    password_hash='test-password-hash',  # noqa: S106
                    status='pending-confirmation',
                    access_version=1,
                    time_zone=None,
                    created_at=expired_at,
                    updated_at=expired_at,
                    confirmed_at=None,
                    deleted_at=None,
                    deletion_reason=None,
                )
                for index in range(count)
            ]
        )
        session.commit()


def _count_accounts_with_status(session: Session, status: str) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(AccountModel)
            .where(AccountModel.status == status)
        )
        or 0
    )


def _count_expiry_requested_events(session: Session) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(EventModel)
            .where(EventModel.name == _ACCOUNT_EXPIRY_REQUESTED_EVENT_NAME)
        )
        or 0
    )
