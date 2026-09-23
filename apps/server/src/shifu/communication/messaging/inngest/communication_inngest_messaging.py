"""Declare the Inngest functions owned by Communication."""

from typing import cast

from inngest import Function, Inngest

from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    EmailDeliveryProvider,
    MessageRenderer,
    SecretEnvelopeProvider,
)
from shifu.communication.core.use_cases import (
    CancelCommunicationUseCase,
    DeliverCommunicationUseCase,
)
from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
from shifu.communication.messaging.inngest.jobs import (
    CancelCommunicationJob,
    DeliverCommunicationJob,
)
from shifu.communication.providers.email import (
    FernetSecretEnvelopeProvider,
    GeneratedEmailMessageRenderer,
    ResendEmailDeliveryProvider,
    SmtpEmailDeliveryProvider,
)
from shifu.shared.constants import EnvironmentSettings
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class CommunicationInngestMessaging:
    """Compose Communication jobs without creating another HTTP endpoint."""

    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        communication_database: CommunicationDatabase | None = None,
        id_provider: IdentifierProvider | None = None,
        clock_provider: ClockProvider | None = None,
        secret_envelope_provider: SecretEnvelopeProvider | None = None,
        message_renderer: MessageRenderer | None = None,
        email_delivery_provider: EmailDeliveryProvider | None = None,
    ) -> list[Function[object]]:
        settings = EnvironmentSettings.from_environment()
        communication_database = (
            communication_database or SqlalchemyCommunicationDatabase()
        )
        id_provider = id_provider or SystemIdentifierProvider()
        clock_provider = clock_provider or SystemClockProvider()
        secret_envelope_provider = (
            secret_envelope_provider
            or FernetSecretEnvelopeProvider(settings.communication_encryption_keys)
        )
        message_renderer = message_renderer or GeneratedEmailMessageRenderer()
        email_delivery_provider = email_delivery_provider or (
            CommunicationInngestMessaging._build_email_delivery_provider(settings)
        )

        delivery_use_case = DeliverCommunicationUseCase(
            communication_database=communication_database,
            id_provider=id_provider,
            clock_provider=clock_provider,
            secret_envelope_provider=secret_envelope_provider,
            message_renderer=message_renderer,
            email_delivery_provider=email_delivery_provider,
        )
        cancellation_use_case = CancelCommunicationUseCase(
            communication_database=communication_database,
            clock_provider=clock_provider,
        )
        return [
            cast(
                'Function[object]',
                DeliverCommunicationJob.handle(inngest, delivery_use_case),
            ),
            cast(
                'Function[object]',
                CancelCommunicationJob.handle(inngest, cancellation_use_case),
            ),
        ]

    @staticmethod
    def _build_email_delivery_provider(
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
