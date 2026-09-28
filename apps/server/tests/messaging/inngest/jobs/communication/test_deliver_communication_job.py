"""Real-runtime coverage for the Communication delivery consumer."""

from typing import TYPE_CHECKING, cast
import json
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest
from sqlalchemy import select

from shifu.communication.core.domain.enums import CommunicationType
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


def _request_password_recovery(fixture: 'InngestFixture') -> None:
    body = json.dumps({'email': 'delivery-job@example.com'}).encode()
    request = Request(  # noqa: S310 - local FastAPI fixture URL
        f'{fixture.server_url}/identity/password-recovery-requests',
        data=body,
        headers={
            'content-type': 'application/json',
            'x-shifu-bff-secret': fixture.bff_shared_secret,
        },
        method='POST',
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310
        assert response.status == 202


def _assert_password_recovery_email(
    fixture: 'InngestFixture',
    message: dict[str, object],
) -> None:
    message_id = message.get('ID')
    assert isinstance(message_id, str)
    with urlopen(  # noqa: S310 - local Mailpit fixture URL
        f'{fixture.mailpit_url}/api/v1/message/{quote(message_id, safe="")}', timeout=10
    ) as response:
        payload: object = json.load(response)
    assert isinstance(payload, dict)
    payload = cast('dict[str, object]', payload)

    subject = payload.get('Subject')
    text_body = payload.get('Text')
    html_body = payload.get('HTML')

    assert subject == 'Redefina sua senha no Shifu'
    assert isinstance(text_body, str)
    assert isinstance(html_body, str)

    body = re.sub(
        r'https?://[^\s"<>]+/reset-password\?token=[^\s"<>]+',
        '<reset-url>',
        f'{text_body}\n{html_body}',
    )
    assert 'Redefina sua senha' in body
    assert (
        'Recebemos uma solicitação para redefinir a senha da sua conta no Shifu.'
        in body
    )
    assert (
        'Use o botão abaixo para criar uma nova senha. Este link é válido por uma hora '
        'e pode ser usado uma única vez.'
    ) in body
    assert 'Por segurança, este link expira em' in body
    assert 'Delivery learner' not in body

    reset_urls = re.findall(r'href="([^\"]*/reset-password\?token=[^\"]+)"', html_body)
    assert len(reset_urls) == 1
    assert re.fullmatch(
        r'https?://[^/]+/reset-password\?token=[A-Za-z0-9_-]+', reset_urls[0]
    )
    assert html_body.count('Redefinir minha senha') == 1


class TestDeliverCommunicationJob:
    def test_registered_id_only_event_delivers_once_after_duplicate_delivery(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        _register_account(inngest_fixture)
        inngest_fixture.wait_for_mail()
        inngest_fixture.clear_mailpit()
        _request_password_recovery(inngest_fixture)
        messages = inngest_fixture.wait_for_mail()
        assert len(messages) == 1
        _assert_password_recovery_email(inngest_fixture, messages[0])

        with inngest_fixture.inspection_session() as session:
            communication = session.scalar(
                select(CommunicationModel)
                .where(CommunicationModel.type == CommunicationType.PASSWORD_RECOVERY)
                .order_by(CommunicationModel.created_at)
            )
            assert communication is not None
            communication_id = communication.id
            assert communication.expires_at is not None

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
