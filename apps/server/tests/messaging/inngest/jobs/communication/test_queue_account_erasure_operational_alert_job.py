"""Real-runtime coverage for the fixed account-erasure alert consumer."""

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast
from urllib.parse import quote
from urllib.request import urlopen
from uuid import UUID

from sqlalchemy import select

from shifu.communication.core.domain.enums import CommunicationType
from shifu.communication.database.sqlalchemy.models import CommunicationModel
from tests.fixtures.telemetry_boundary_fixture import telemetry_inngest_app_target

inngest_app_target = telemetry_inngest_app_target

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


class TestQueueAccountErasureOperationalAlertJob:
    def test_repeated_incident_queues_one_fixed_non_personal_email(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        erasure_id = UUID('44c3e3b4-c9db-4c8a-a347-ec9109f69b62')
        incident_id = UUID('2c6903ba-f5bd-4f14-9f6d-8849c16371a7')
        payload: dict[str, object] = {
            'erasure_id': str(erasure_id),
            'module': 'learning',
            'failure_code': 'erasure_deadline_exceeded',
            'closed_at': '2026-11-20T14:00:00+00:00',
            'due_at': '2026-11-21T14:00:00+00:00',
            'incident_id': str(incident_id),
        }

        inngest_fixture.publish(
            'identity/account-erasure.operational-alert.requested',
            payload,
            f'{incident_id}-first',
        )
        messages = inngest_fixture.wait_for_mail()
        assert len(messages) == 1
        self._assert_fixed_alert(inngest_fixture, messages[0], payload)

        inngest_fixture.publish(
            'identity/account-erasure.operational-alert.requested',
            payload,
            f'{incident_id}-replayed',
        )
        try:
            inngest_fixture.wait_for_mail_count(2, timeout=5)
        except AssertionError:
            pass
        else:
            raise AssertionError('Repeated incident sent another operational alert')

        with inngest_fixture.inspection_session() as session:
            communications = session.scalars(
                select(CommunicationModel).where(
                    CommunicationModel.type
                    == CommunicationType.ACCOUNT_ERASURE_ALERT.value
                )
            ).all()

        assert len(communications) == 1
        communication = communications[0]
        assert communication.status == 'sent'
        assert communication.account_id is None
        assert communication.identity_action_token_id is None
        assert communication.recipient_email == 'shifu.ctrlaltdel@gmail.com'
        assert communication.idempotency_key == f'account-erasure-alert:{incident_id}'

    @staticmethod
    def _assert_fixed_alert(
        fixture: 'InngestFixture',
        message: dict[str, object],
        payload: Mapping[str, object],
    ) -> None:
        message_id = message.get('ID')
        assert isinstance(message_id, str)
        with urlopen(  # noqa: S310 - local Mailpit fixture URL
            f'{fixture.mailpit_url}/api/v1/message/{quote(message_id, safe="")}',
            timeout=10,
        ) as response:
            raw_message: object = json.load(response)
        assert isinstance(raw_message, dict)
        stored = cast('dict[str, object]', raw_message)
        assert stored.get('To') == 'shifu.ctrlaltdel@gmail.com'
        assert stored.get('Subject') == 'Alerta de limpeza de conta pendente no Shifu'
        text_body = stored.get('Text')
        html_body = stored.get('HTML')
        assert isinstance(text_body, str)
        assert isinstance(html_body, str)
        rendered = f'{text_body}\n{html_body}'
        erasure_id = payload.get('erasure_id')
        module = payload.get('module')
        failure_code = payload.get('failure_code')
        assert isinstance(erasure_id, str)
        assert isinstance(module, str)
        assert isinstance(failure_code, str)
        for value in (
            erasure_id,
            module,
            failure_code,
            '2026-11-20 14:00 UTC',
            '2026-11-21 14:00 UTC',
        ):
            assert value in rendered
        for private_value in ('learner@example.com', 'account_id', 'victim name'):
            assert private_value not in rendered
