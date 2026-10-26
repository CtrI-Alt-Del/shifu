"""Real-runtime coverage for the Communication delivery consumer."""

import json
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest
from shifu.communication.core.domain.enums import CommunicationType
from shifu.communication.core.domain.events import (
    CommunicationQueuedEvent,
    CommunicationQueuedPayload,
)
from shifu.communication.database.sqlalchemy.models import (
    CommunicationModel,
    DeliveryAttemptModel,
)
from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from sqlalchemy import select
from tests.fixtures.telemetry_boundary_fixture import (
    read_job_telemetry,
    telemetry_inngest_app_target,
)

inngest_app_target = telemetry_inngest_app_target


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

    def test_mapping_failure_emits_failure_retry_and_recovers_on_real_runtime(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        assert inngest_fixture.runtime_environment is not None
        control = Path(
            inngest_fixture.runtime_environment['SHIFU_TEST_TELEMETRY_CONTROL']
        )
        identifier = IdProviderFaker().generate()
        # A missing communication normally completes without a write. The public
        # SDK middleware injects a mapping failure before the first durable step.
        # This proves wrapper failure/retry behavior, not database-step telemetry.
        event = CommunicationQueuedEvent(
            payload=CommunicationQueuedPayload(communication_id=identifier)
        )
        control.write_text('mapping-failure')
        try:
            inngest_fixture.publish(
                event.name, {'communication_id': identifier}, identifier
            )
            inngest_fixture.wait_for_log(
                f'"event":"job.retrying","event_id":"{identifier}"', timeout=90
            )
        finally:
            control.unlink(missing_ok=True)
        inngest_fixture.wait_for_log(
            f'"event":"job.completed","event_id":"{identifier}"', timeout=90
        )
        events = [
            entry
            for entry in read_job_telemetry(inngest_fixture.runtime_environment)
            if entry.get('event_id') == identifier
        ]
        names = [entry['event'] for entry in events]
        assert names[:3] == ['job.started', 'job.failed', 'job.retrying']
        assert names[-1] == 'job.completed'
        assert names.count('job.completed') == 1
        failure = next(entry for entry in events if entry['event'] == 'job.failed')
        assert failure.get('error_code') == 'job_failed'
        assert failure.get('exception_type') == 'RuntimeError'
        retry = next(entry for entry in events if entry['event'] == 'job.retrying')
        assert retry.get('result') == 'retry'
        completed = events[-1]
        attempt = completed.get('attempt')
        # Inngest's attempt counter belongs to the current callback/step. A
        # later successful step resets it, even within this same recovered run.
        assert isinstance(attempt, int) and attempt >= 1
        callback_attempts = [entry.get('attempt') for entry in events]
        assert all(isinstance(value, int) and value >= 1 for value in callback_attempts)
        retried_starts = [
            entry.get('attempt') for entry in events if entry['event'] == 'job.started'
        ]
        assert any(isinstance(value, int) and value >= 2 for value in retried_starts)
        assert failure.get('attempt') == 1
        assert retry.get('attempt') == 1
        assert completed.get('result') == 'success'
        assert all(
            entry.get('job') == 'communication.deliver_communication'
            for entry in events
        )
        assert all(entry.get('run_id') == completed.get('run_id') for entry in events)
        assert all(entry.get('event_id') == identifier for entry in events)
        with inngest_fixture.inspection_session() as session:
            assert session.get(CommunicationModel, identifier) is None
            assert (
                session.scalars(
                    select(DeliveryAttemptModel).where(
                        DeliveryAttemptModel.communication_id == identifier
                    )
                ).all()
                == []
            )

    def test_invalid_registered_event_reports_failure_without_runtime_retry_or_delivery(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        event_id = IdProviderFaker().generate()
        event = CommunicationQueuedEvent(
            payload=CommunicationQueuedPayload(communication_id='missing-communication')
        )
        submitted_ids = inngest_fixture.publish(
            event.name,
            {'communication_id': '', 'secret': 'must-not-be-copied'},
            event_id,
        )
        assert len(submitted_ids) == 1
        started = json.loads(
            inngest_fixture.wait_for_log(
                f'"event":"job.started","event_id":"{event_id}"', timeout=90
            )
        )
        assert isinstance(started['run_id'], str) and started['run_id']
        # The publish acknowledgment precedes asynchronous event/run storage.
        # Observe the registered job before querying that run's persisted status.
        # Known invalid input raises NonRetriableError inside a durable step.
        # Inspect the actual terminal state instead of claiming a wrapper retry.
        query = """
            query InvalidCommunicationRun($id: ULID!) {
                eventV2(id: $id) { runs { id status } }
            }
        """
        deadline = time.monotonic() + 90
        runs: list[object] = []
        while time.monotonic() < deadline:
            data = inngest_fixture.query_inngest(query, {'id': submitted_ids[0]})
            observed = data.get('eventV2')
            assert isinstance(observed, dict)
            current: object = cast('dict[str, object]', observed).get('runs')
            assert isinstance(current, list)
            runs = cast('list[object]', current)
            if runs and all(
                isinstance(run, dict)
                and cast('dict[str, object]', run).get('status') == 'FAILED'
                for run in runs
            ):
                break
            time.sleep(0.1)
        else:
            pytest.fail(f'Invalid communication did not fail terminally: {runs!r}')

        assert len(runs) == 1
        assert cast('dict[str, object]', runs[0])['id'] == started['run_id']
        events = [
            entry
            for entry in read_job_telemetry(inngest_fixture.runtime_environment)
            if entry.get('event_id') == event_id
        ]
        assert events
        assert events[0]['event'] == 'job.started'
        assert all(
            entry.get('run_id') == cast('dict[str, object]', runs[0])['id']
            for entry in events
        )
        assert all(
            entry.get('job') == 'communication.deliver_communication'
            for entry in events
        )
        assert all(entry.get('attempt') == 1 for entry in events)
        assert [entry['event'] for entry in events] == [
            'job.started',
            'job.failed',
            'job.retrying',
        ]
        failed = events[1]
        assert failed.get('error_code') == 'job_failed'
        assert failed.get('exception_type') == 'NonRetriableError'
        assert failed.get('result') == 'failure'
        # The existing wrapper emits retry intent for every early exception.
        # This marker does not prove a retry: the engine failed terminally after
        # exactly one started callback, with no delivery or persistence effect.
        retrying = events[2]
        assert retrying.get('error_code') == 'job_failed'
        assert retrying.get('result') == 'retry'
        assert 'secret' not in str(events)
        assert 'must-not-be-copied' not in str(events)
        assert inngest_fixture.mailpit_messages() == []
        with inngest_fixture.inspection_session() as session:
            assert session.scalars(select(DeliveryAttemptModel)).all() == []
            assert session.scalars(select(CommunicationModel)).all() == []
