from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, cast

from shifu.communication.core.domain.structures import DeliveryOutcome, EmailMessage

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Protocol

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
    ) -> None:
        self._api_key = api_key
        self._sender = sender
        self._timeout_seconds = timeout_seconds

    def send(self, message: EmailMessage) -> DeliveryOutcome:
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
            return DeliveryOutcome.accepted(
                provider_message_id if isinstance(provider_message_id, str) else None
            )
        except Exception as error:  # noqa: BLE001 - provider boundary maps safely.
            return self._map_error(error)

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
