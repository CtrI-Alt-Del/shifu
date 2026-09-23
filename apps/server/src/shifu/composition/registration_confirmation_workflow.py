from __future__ import annotations

from urllib.parse import urlencode
from typing import TYPE_CHECKING

from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationType,
)
from shifu.communication.core.domain.structures import (
    CommunicationRequest,
    MessageTemplateValues,
)
from shifu.communication.core.use_cases import QueueCommunicationUseCase
from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
from shifu.communication.providers.email import (
    FernetSecretEnvelopeProvider,
    GeneratedEmailMessageRenderer,
    ResendEmailDeliveryProvider,
    SmtpEmailDeliveryProvider,
)
from shifu.identity.core.domain.enums import ConfirmationDeliveryQueueStatus
from shifu.identity.core.interfaces import ConfirmationDeliveryResult

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from shifu.communication.core.interfaces import (
        CommunicationDatabase,
        EmailDeliveryProvider,
        MessageRendererProvider,
        SecretEnvelopeProvider,
    )
    from shifu.identity.core.interfaces import ConfirmationDeliveryRequest
    from shifu.shared.constants import EnvironmentSettings
    from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class RegistrationConfirmationWorkflow:
    """Compose Identity's post-commit output port with Communication adapters."""

    def __init__(
        self,
        communication_database: CommunicationDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        secret_envelope_provider: SecretEnvelopeProvider,
        action_origin: str,
    ) -> None:
        self._queue = QueueCommunicationUseCase(
            communication_database=communication_database,
            id_provider=id_provider,
            clock_provider=clock_provider,
            secret_envelope_provider=secret_envelope_provider,
        )
        self._action_origin = action_origin.rstrip('/')

    @classmethod
    def from_environment(
        cls,
        *,
        engine: Engine,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        settings: EnvironmentSettings,
    ) -> RegistrationConfirmationWorkflow:
        return cls(
            communication_database=SqlalchemyCommunicationDatabase(
                engine=engine,
                id_provider=id_provider,
            ),
            id_provider=id_provider,
            clock_provider=clock_provider,
            secret_envelope_provider=FernetSecretEnvelopeProvider(
                settings.communication_encryption_keys
            ),
            action_origin=settings.confirmation_action_origin,
        )

    def queue(
        self,
        request: ConfirmationDeliveryRequest,
    ) -> ConfirmationDeliveryResult:
        try:
            self._queue.execute(
                CommunicationRequest(
                    communication_id=request.communication_id,
                    identity_confirmation_id=request.identity_confirmation_id,
                    account_id=request.account_id,
                    type=CommunicationType.ACCOUNT_CONFIRMATION,
                    channel=CommunicationChannel.EMAIL,
                    recipient_email=request.recipient_email,
                    recipient_name=request.recipient_name,
                    message_values=MessageTemplateValues(
                        display_name=request.recipient_name,
                        action_url=self._confirmation_url(request.confirmation_token),
                        expires_at=request.expires_at,
                    ),
                    idempotency_key=request.communication_id,
                )
            )
        except Exception:  # noqa: BLE001 - queue failure is a recoverable state.
            return ConfirmationDeliveryResult(
                status=ConfirmationDeliveryQueueStatus.DELIVERY_UNAVAILABLE
            )
        return ConfirmationDeliveryResult(status=ConfirmationDeliveryQueueStatus.QUEUED)

    def _confirmation_url(self, token: str) -> str:
        return f'{self._action_origin}/confirm-email?{urlencode({"token": token})}'


def build_message_renderer() -> MessageRendererProvider:
    return GeneratedEmailMessageRenderer()


def build_secret_envelope_provider(
    settings: EnvironmentSettings,
) -> SecretEnvelopeProvider:
    return FernetSecretEnvelopeProvider(settings.communication_encryption_keys)


def build_email_delivery_provider(
    settings: EnvironmentSettings,
) -> EmailDeliveryProvider:
    if settings.email_provider == 'resend':
        if settings.resend_api_key is None or settings.resend_from is None:
            raise ValueError('Resend configuration is incomplete')
        return ResendEmailDeliveryProvider(
            api_key=settings.resend_api_key,
            sender=settings.resend_from,
            timeout_seconds=settings.email_timeout_seconds,
        )
    return SmtpEmailDeliveryProvider(
        host=settings.smtp_host,
        port=settings.smtp_port,
        sender=settings.email_from,
        username=settings.smtp_username,
        password=settings.smtp_password,
        timeout_seconds=settings.email_timeout_seconds,
        start_tls=settings.smtp_start_tls,
        use_tls=settings.smtp_use_tls,
    )
