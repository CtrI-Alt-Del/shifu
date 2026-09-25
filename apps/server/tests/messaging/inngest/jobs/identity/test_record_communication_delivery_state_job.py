"""Real-runtime coverage for Identity's safe delivery-state projection."""

from typing import TYPE_CHECKING
import json
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from shifu.communication.core.domain.enums import CommunicationDeliveryState
from shifu.communication.core.domain.events import (
    CommunicationDeliveryStateChangedEvent,
    CommunicationDeliveryStateChangedPayload,
)
from shifu.communication.database.sqlalchemy.models import CommunicationModel
from shifu.identity.database.sqlalchemy.models import AccountActionTokenModel

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


def _register_account(fixture: 'InngestFixture') -> None:
    body = json.dumps(
        {
            'display_name': 'Delivery-state learner',
            'email': 'delivery-state-job@example.com',
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


class TestRecordCommunicationDeliveryStateJob:
    def test_correlated_terminal_state_is_recorded_once(
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
            identity_confirmation_id = communication.identity_confirmation_id
            assert identity_confirmation_id is not None

        inngest_fixture.wait_for_database(
            lambda session: _has_delivery_state(
                session,
                identity_confirmation_id,
                'delivered',
            )
        )

        with inngest_fixture.inspection_session() as session:
            token = session.get(AccountActionTokenModel, identity_confirmation_id)
            assert token is not None
            token.delivery_status = None
            session.commit()
            communication_id = communication.id

        state_event = CommunicationDeliveryStateChangedEvent(
            payload=CommunicationDeliveryStateChangedPayload(
                communication_id=communication_id,
                identity_confirmation_id=identity_confirmation_id,
                state=CommunicationDeliveryState.PERMANENT_FAILURE,
            )
        )
        inngest_fixture.publish(
            state_event.name,
            {
                'communication_id': state_event.payload.communication_id,
                'identity_confirmation_id': state_event.payload.identity_confirmation_id,
                'state': CommunicationDeliveryState.PERMANENT_FAILURE.value,
                'unexpected': 'rejected by the strict transport schema',
            },
            f'{communication_id}-malformed',
        )

        with inngest_fixture.inspection_session() as session:
            token = session.get(AccountActionTokenModel, identity_confirmation_id)
        assert token is not None
        assert token.delivery_status is None

        inngest_fixture.publish(
            state_event.name,
            {
                'communication_id': state_event.payload.communication_id,
                'identity_confirmation_id': state_event.payload.identity_confirmation_id,
                'state': CommunicationDeliveryState.PERMANENT_FAILURE.value,
            },
            f'{communication_id}-permanent-failure',
        )
        inngest_fixture.wait_for_database(
            lambda session: _has_delivery_state(
                session,
                identity_confirmation_id,
                'permanent_failure',
            )
        )

        inngest_fixture.publish(
            state_event.name,
            {
                'communication_id': state_event.payload.communication_id,
                'identity_confirmation_id': state_event.payload.identity_confirmation_id,
                'state': CommunicationDeliveryState.PERMANENT_FAILURE.value,
            },
            f'{communication_id}-permanent-failure-duplicate',
        )
        inngest_fixture.wait_for_database(
            lambda session: _has_delivery_state(
                session,
                identity_confirmation_id,
                'permanent_failure',
            )
        )


def _has_delivery_state(
    session: Session,
    identity_confirmation_id: str,
    expected_state: str,
) -> bool:
    token = session.get(AccountActionTokenModel, identity_confirmation_id)
    return token is not None and token.delivery_status == expected_state
