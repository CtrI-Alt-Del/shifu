"""Real-runtime coverage for cancellation and expiry redaction."""

from typing import TYPE_CHECKING
import json
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from shifu.communication.database.sqlalchemy.models import CommunicationModel
from shifu.identity.core.domain.enums import AccountConfirmationCancellationReason
from shifu.identity.core.domain.events import (
    AccountConfirmationCancelledEvent,
    AccountConfirmationCancelledPayload,
)

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


def _register_account(fixture: 'InngestFixture') -> None:
    body = json.dumps(
        {
            'display_name': 'Cancellation learner',
            'email': 'cancellation-job@example.com',
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


class TestCancelCommunicationJob:
    def test_expired_cancellation_redacts_a_delivered_request_and_is_idempotent(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        _register_account(inngest_fixture)
        inngest_fixture.wait_for_mail()

        with inngest_fixture.inspection_session() as session:
            communication = session.scalar(
                select(CommunicationModel).order_by(CommunicationModel.created_at)
            )
            assert communication is not None
            communication_id = communication.id
            identity_confirmation_id = communication.identity_confirmation_id
            assert identity_confirmation_id is not None

        cancellation = AccountConfirmationCancelledEvent(
            payload=AccountConfirmationCancelledPayload(
                communication_id=communication_id,
                identity_confirmation_id=identity_confirmation_id,
                reason=AccountConfirmationCancellationReason.EXPIRED,
            )
        )

        inngest_fixture.publish(
            cancellation.name,
            {
                'communication_id': cancellation.payload.communication_id,
                'identity_confirmation_id': cancellation.payload.identity_confirmation_id,
                'reason': cancellation.payload.reason.value,
                'unexpected': 'rejected by the strict transport schema',
            },
            f'{communication_id}-malformed',
        )

        with inngest_fixture.inspection_session() as session:
            unchanged = session.get(CommunicationModel, communication_id)
        assert unchanged is not None
        assert unchanged.recipient_email is not None
        assert unchanged.identity_confirmation_id == identity_confirmation_id

        inngest_fixture.publish(
            cancellation.name,
            {
                'communication_id': cancellation.payload.communication_id,
                'identity_confirmation_id': cancellation.payload.identity_confirmation_id,
                'reason': cancellation.payload.reason.value,
            },
            f'{communication_id}-expired',
        )
        inngest_fixture.wait_for_database(
            lambda session: _is_redacted(session, communication_id)
        )

        inngest_fixture.publish(
            cancellation.name,
            {
                'communication_id': cancellation.payload.communication_id,
                'identity_confirmation_id': cancellation.payload.identity_confirmation_id,
                'reason': cancellation.payload.reason.value,
            },
            f'{communication_id}-expired-duplicate',
        )
        inngest_fixture.wait_for_database(
            lambda session: _is_redacted(session, communication_id)
        )


def _is_redacted(session: Session, communication_id: str) -> bool:
    communication = session.get(CommunicationModel, communication_id)
    return (
        communication is not None
        and communication.status == 'sent'
        and communication.account_id is None
        and communication.recipient_email is None
        and communication.identity_confirmation_id is None
        and communication.encrypted_content is None
    )
