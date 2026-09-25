"""Real-runtime coverage for expiry child execution and redaction."""

from datetime import timedelta
from typing import TYPE_CHECKING
import json
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from shifu.identity.core.domain.events import (
    AccountExpiryRequestedEvent,
    AccountExpiryRequestedPayload,
)
from shifu.identity.database.sqlalchemy.models import (
    AccountActionTokenModel,
    AccountModel,
)
from shifu.communication.database.sqlalchemy.models import CommunicationModel

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


def _register_account(fixture: 'InngestFixture') -> None:
    body = json.dumps(
        {
            'display_name': 'Expiry learner',
            'email': 'expiry-job@example.com',
            'password': 'Password123!',
        }
    ).encode()
    request = Request(  # noqa: S310 - local FastAPI fixture URL
        f'{fixture.server_url}/identity/registrations',
        data=body,
        headers={
            'content-type': 'application/json',
            'x-shifu-bff-secret': fixture.bff_shared_secret,
        },
        method='POST',
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310
        assert response.status == 202


class TestExpireUnconfirmedAccountsJob:
    def test_registered_expiry_event_expires_account_and_redacts_delivery(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        _register_account(inngest_fixture)
        inngest_fixture.wait_for_mail()

        with inngest_fixture.inspection_session() as session:
            account = session.scalar(
                select(AccountModel).order_by(AccountModel.created_at)
            )
            communication = session.scalar(
                select(CommunicationModel).order_by(CommunicationModel.created_at)
            )
            assert account is not None
            assert communication is not None
            account_id = account.id
            communication_id = communication.id
            original_access_version = account.access_version
            account.created_at = account.created_at - timedelta(days=8)
            account.updated_at = account.created_at
            session.commit()

        event = AccountExpiryRequestedEvent(
            payload=AccountExpiryRequestedPayload(account_id=account_id)
        )
        inngest_fixture.publish(
            event.name,
            {'account_id': event.payload.account_id},
            f'{account_id}-expiry',
        )
        inngest_fixture.wait_for_database(
            lambda session: _is_expired_and_redacted(
                session,
                account_id,
                communication_id,
                original_access_version,
            )
        )

        inngest_fixture.publish(
            event.name,
            {'account_id': event.payload.account_id},
            f'{account_id}-expiry-duplicate',
        )
        inngest_fixture.wait_for_database(
            lambda session: _is_expired_and_redacted(
                session,
                account_id,
                communication_id,
                original_access_version,
            )
        )


def _is_expired_and_redacted(
    session: Session,
    account_id: str,
    communication_id: str,
    original_access_version: int,
) -> bool:
    account = session.get(AccountModel, account_id)
    token = session.scalar(
        select(AccountActionTokenModel).where(
            AccountActionTokenModel.account_id == account_id
        )
    )
    communication = session.get(CommunicationModel, communication_id)
    return (
        account is not None
        and account.status == 'deleted'
        and account.deletion_reason == 'unconfirmed-account-expired'
        and account.deleted_at is not None
        and account.access_version == original_access_version + 1
        and token is not None
        and token.status == 'expired'
        and communication is not None
        and communication.account_id is None
        and communication.recipient_email is None
        and communication.identity_confirmation_id is None
        and communication.encrypted_content is None
    )
