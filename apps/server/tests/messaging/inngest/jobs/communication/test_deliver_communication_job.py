"""Real-runtime coverage for the Communication delivery consumer."""

from typing import TYPE_CHECKING
import json
from urllib.request import Request, urlopen

import pytest
from sqlalchemy import select

from shifu.communication.core.domain.events import (
    CommunicationQueuedEvent,
    CommunicationQueuedPayload,
)
from shifu.communication.database.sqlalchemy.models import (
    CommunicationModel,
    DeliveryAttemptModel,
)

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


def _register_account(fixture: 'InngestFixture') -> None:
    body = json.dumps(
        {
            'display_name': 'Delivery learner',
            'email': 'delivery-job@example.com',
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


class TestDeliverCommunicationJob:
    def test_registered_id_only_event_delivers_once_after_duplicate_delivery(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        _register_account(inngest_fixture)
        messages = inngest_fixture.wait_for_mail()
        assert len(messages) == 1

        with inngest_fixture.inspection_session() as session:
            communication = session.scalar(
                select(CommunicationModel).order_by(CommunicationModel.created_at)
            )
            assert communication is not None
            communication_id = communication.id

        event = CommunicationQueuedEvent(
            payload=CommunicationQueuedPayload(communication_id=communication_id)
        )
        inngest_fixture.publish(
            event.name,
            {'communication_id': event.payload.communication_id},
            f'{communication_id}-duplicate',
        )

        with pytest.raises(AssertionError):
            inngest_fixture.wait_for_mail_count(2, timeout=5)

        with inngest_fixture.inspection_session() as session:
            persisted = session.get(CommunicationModel, communication_id)
            attempts = session.scalars(
                select(DeliveryAttemptModel).where(
                    DeliveryAttemptModel.communication_id == communication_id
                )
            ).all()

        assert persisted is not None
        assert persisted.status == 'sent'
        assert persisted.attempt_count == 1
        assert len(attempts) == 1
