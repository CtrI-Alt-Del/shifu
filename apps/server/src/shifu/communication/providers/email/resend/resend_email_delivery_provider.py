from __future__ import annotations

from importlib import import_module
from time import perf_counter
from typing import TYPE_CHECKING, cast

from shifu.communication.core.domain.structures import DeliveryOutcome, EmailMessage

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Protocol

    from shifu.shared.core.interfaces.telemetry_provider import (
        TelemetryEventInput,
        TelemetryProvider,
    )

    class _ResendEmails(Protocol):
        def send(
            self,
            params: Mapping[str, object],
            *,
            options: Mapping[str, str],
        ) -> Mapping[str, object]: ...

    class _ResendModule(Protocol):
        api_key: str
        Emails: _ResendEmails
        default_http_client: object


class ResendEmailDeliveryProvider:
    """Use the Resend SDK with the stable Communication idempotency key."""

    def __init__(
        self,
        *,
        api_key: str,
        sender: str,
        timeout_seconds: float = 10.0,
        telemetry_provider: TelemetryProvider | None = None,
    ) -> None:
        self._api_key = api_key
        self._sender = sender
        self._timeout_seconds = timeout_seconds
        self._telemetry_provider = telemetry_provider

    def send(self, message: EmailMessage) -> DeliveryOutcome:
        started_at = perf_counter()
        self._emit(
            {
                'level': 'INFO',
                'event': 'integration.operation.started',
                'operation': 'resend.send',
                'integration': 'resend',
                'event_id': message.idempotency_key,
            }
        )
        exception_type: str | None = None
        try:
            resend = cast('_ResendModule', import_module('resend'))
            resend.api_key = self._api_key
            self._configure_timeout(resend)
            emails = resend.Emails
            response = emails.send(
                {
                    'from': self._sender,
                    'to': [message.to],
                    'subject': message.subject,
                    'html': message.html,
                    **({'text': message.text} if message.text is not None else {}),
                },
                options={'idempotency_key': message.idempotency_key},
            )
            provider_message_id = response.get('id')
            outcome = DeliveryOutcome.accepted(
                provider_message_id if isinstance(provider_message_id, str) else None
            )
        except Exception as error:  # noqa: BLE001 - provider boundary maps safely.
            exception_type = type(error).__name__
            outcome = self._map_error(error)

        if outcome.succeeded:
            self._emit(
                {
                    'level': 'INFO',
                    'event': 'integration.operation.completed',
                    'operation': 'resend.send',
                    'integration': 'resend',
                    'event_id': message.idempotency_key,
                    'result': 'success',
                    'duration_ms': _duration_ms(started_at),
                }
            )
        else:
            error_code = (
                'integration_unavailable' if outcome.retryable else 'integration_failed'
            )
            self._emit(
                {
                    'level': 'ERROR',
                    'event': 'integration.operation.failed',
                    'operation': 'resend.send',
                    'integration': 'resend',
                    'event_id': message.idempotency_key,
                    'result': 'failure',
                    'error_code': error_code,
                    'exception_type': exception_type,
                    'duration_ms': _duration_ms(started_at),
                }
            )
            if outcome.retryable:
                self._emit(
                    {
                        'level': 'WARNING',
                        'event': 'integration.operation.retrying',
                        'operation': 'resend.send',
                        'integration': 'resend',
                        'event_id': message.idempotency_key,
                        'result': 'retry',
                        'error_code': 'integration_unavailable',
                    }
                )
        return outcome

    def _emit(self, event: Mapping[str, object]) -> None:
        if self._telemetry_provider is None:
            return
        telemetry_event = cast('TelemetryEventInput', dict(event))
        if telemetry_event.get('exception_type') is None:
            telemetry_event.pop('exception_type', None)
        try:
            self._telemetry_provider.emit(telemetry_event)
        except Exception:  # noqa: BLE001 - telemetry is best effort.
            return

    def _configure_timeout(self, resend: _ResendModule) -> None:
        try:
            client_module = import_module('resend.http_client_requests')
            client_type = cast(
                'Callable[..., object]',
                getattr(client_module, 'RequestsClient'),  # noqa: B009
            )
            resend.default_http_client = client_type(timeout=self._timeout_seconds)
        except (ImportError, AttributeError, TypeError):
            # The SDK's default client remains a safe fallback when an installed
            # minor version does not expose the optional RequestsClient helper.
            return

    @staticmethod
    def _map_error(error: Exception) -> DeliveryOutcome:
        status_code = getattr(error, 'status_code', None)
        if not isinstance(status_code, int):
            status_code = getattr(error, 'code', None)
        if isinstance(status_code, int) and status_code in {400, 401, 403, 404, 422}:
            return DeliveryOutcome.permanent_failure('resend_permanent_rejection')
        if isinstance(status_code, int) and status_code >= 500:
            return DeliveryOutcome.temporary_failure('resend_temporary_failure')
        if isinstance(status_code, int) and status_code == 429:
            return DeliveryOutcome.temporary_failure('resend_rate_limited')
        return DeliveryOutcome.temporary_failure('resend_unavailable')


def _duration_ms(started_at: float) -> float:
    return max((perf_counter() - started_at) * 1000, 0.0)
