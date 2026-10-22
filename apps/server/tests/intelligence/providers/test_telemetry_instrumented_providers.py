from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import httpx
import pytest

from shifu.communication.core.domain.structures import EmailMessage
from shifu.communication.providers.email.resend.resend_email_delivery_provider import (
    ResendEmailDeliveryProvider,
)
from shifu.intelligence.providers.mentor_review_provider.openrouter import (
    openrouter_jev_mentor_review_provider as review_module,
)
from shifu.intelligence.providers.mentor_review_provider.openrouter.openrouter_jev_mentor_review_provider import (
    OpenrouterJevMentorReviewProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from shifu.intelligence.core.domain.structures.mentor_generation_request import (
        MentorGenerationRequest,
    )
    from shifu.intelligence.core.domain.structures.mentor_response_block import (
        MentorResponseBlock,
    )
    from shifu.shared.core.interfaces.telemetry_provider import TelemetryEventInput


class _TelemetrySink:
    def __init__(self) -> None:
        self.events: list[TelemetryEventInput] = []

    def emit(self, event: TelemetryEventInput) -> None:
        self.events.append(event)


class _FailingTelemetrySink:
    def emit(self, event: TelemetryEventInput) -> None:
        del event
        raise RuntimeError('telemetry sink unavailable')


class _ResendError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f'Resend returned {status_code}')
        self.status_code = status_code


def _message() -> EmailMessage:
    return EmailMessage(
        idempotency_key='message-1',
        to='learner@example.com',
        subject='Subject',
        html='<p>Body</p>',
        text='Body',
    )


def _resend_module(send: Callable[..., object]) -> SimpleNamespace:
    return SimpleNamespace(
        api_key=None,
        Emails=SimpleNamespace(send=send),
        default_http_client=None,
    )


def _importer(modules: Mapping[str, object]) -> Callable[[str], object]:
    def import_module(name: str) -> object:
        try:
            return modules[name]
        except KeyError:
            raise ImportError(name) from None

    return import_module


def test_resend_emits_completed_telemetry_and_configures_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def send(_params: object, *, options: Mapping[str, str]) -> Mapping[str, object]:
        return {'id': options['idempotency_key']}

    def request_client(**kwargs: object) -> dict[str, object]:
        return kwargs

    sink = _TelemetrySink()
    module = _resend_module(send)
    imports = {
        'resend': module,
        'resend.http_client_requests': SimpleNamespace(RequestsClient=request_client),
    }
    monkeypatch.setattr(
        'shifu.communication.providers.email.resend.resend_email_delivery_provider.import_module',
        _importer(imports),
    )

    outcome = ResendEmailDeliveryProvider(
        api_key='resend-key',
        sender='no-reply@example.com',
        timeout_seconds=4.5,
        telemetry_provider=sink,
    ).send(_message())

    assert outcome.succeeded
    assert outcome.provider_message_id == 'message-1'
    assert module.api_key == 'resend-key'
    assert module.default_http_client == {'timeout': 4.5}
    assert [event['event'] for event in sink.events] == [
        'integration.operation.started',
        'integration.operation.completed',
    ]


@pytest.mark.parametrize(
    ('status_code', 'error_code', 'retryable'),
    ((400, 'integration_failed', False), (503, 'integration_unavailable', True)),
)
def test_resend_emits_failure_and_retry_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    error_code: str,
    retryable: bool,
) -> None:
    def send(_params: object, *, options: Mapping[str, str]) -> Mapping[str, object]:
        del options
        raise _ResendError(status_code)

    sink = _TelemetrySink()
    module = _resend_module(send)
    monkeypatch.setattr(
        'shifu.communication.providers.email.resend.resend_email_delivery_provider.import_module',
        _importer({'resend': module}),
    )

    outcome = ResendEmailDeliveryProvider(
        api_key='resend-key',
        sender='no-reply@example.com',
        telemetry_provider=sink,
    ).send(_message())

    assert not outcome.succeeded
    assert outcome.retryable is retryable
    assert sink.events[-1]['event'] == (
        'integration.operation.retrying'
        if retryable
        else 'integration.operation.failed'
    )
    failed = next(
        event
        for event in sink.events
        if event['event'] == 'integration.operation.failed'
    )
    assert failed.get('error_code') == error_code


def test_resend_ignores_telemetry_sink_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def send(_params: object, *, options: Mapping[str, str]) -> Mapping[str, object]:
        del options
        return {'id': 'message-1'}

    module = _resend_module(send)
    monkeypatch.setattr(
        'shifu.communication.providers.email.resend.resend_email_delivery_provider.import_module',
        _importer({'resend': module}),
    )

    outcome = ResendEmailDeliveryProvider(
        api_key='resend-key',
        sender='no-reply@example.com',
        telemetry_provider=_FailingTelemetrySink(),
    ).send(_message())

    assert outcome.succeeded


def _review_provider(
    *,
    api_key: str | None = None,
    client: object | None = None,
    telemetry_provider: _TelemetrySink | None = None,
) -> OpenrouterJevMentorReviewProvider:
    criteria = (
        'request_adherence',
        'fact_fidelity',
        'cumulative_solution',
        'diagnostic_safety',
        'privacy_access',
        'official_action_claims',
    )
    return OpenrouterJevMentorReviewProvider(
        client=cast('httpx.Client', client if client is not None else object()),
        api_key=api_key,
        decisions_url='https://openrouter.example/decisions',
        thresholds=dict.fromkeys(criteria, 0.5),
        telemetry_provider=telemetry_provider,
    )


def test_openrouter_review_emits_failure_telemetry_when_unavailable() -> None:
    sink = _TelemetrySink()
    request = cast('MentorGenerationRequest', object())
    candidate = cast('MentorResponseBlock', object())

    with pytest.raises(ServiceUnavailableError):
        _review_provider(telemetry_provider=sink).review(request, candidate)

    assert [event['event'] for event in sink.events] == [
        'integration.operation.started',
        'integration.operation.failed',
    ]
    assert sink.events[-1].get('error_code') == 'integration_unavailable'


@pytest.mark.parametrize('transport_failure', [False, True])
def test_openrouter_emits_retry_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    transport_failure: bool,
) -> None:
    class _Client:
        def post(self, *_args: object, **_kwargs: object) -> httpx.Response:
            if transport_failure:
                raise httpx.ConnectError('connection refused')
            return httpx.Response(
                503,
                request=httpx.Request('POST', 'https://openrouter.example/decisions'),
                json={},
            )

    def no_op(*_args: object, **_kwargs: object) -> None:
        return

    def no_sleep(_seconds: float) -> None:
        return

    monkeypatch.setattr(review_module, 'assert_inference_ready', no_op)
    monkeypatch.setattr(review_module, 'report_inference_usage', no_op)
    monkeypatch.setattr(review_module, 'sleep', no_sleep)
    sink = _TelemetrySink()
    request = cast(
        'Callable[[dict[str, object]], object]',
        object.__getattribute__(
            _review_provider(
                api_key='openrouter-key',
                client=_Client(),
                telemetry_provider=sink,
            ),
            '_request',
        ),
    )

    with pytest.raises(ServiceUnavailableError):
        request({'payload': True})

    assert [event['event'] for event in sink.events] == [
        'integration.operation.retrying',
        'integration.operation.retrying',
    ]
