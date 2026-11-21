"""Declare the Inngest functions owned by Communication."""

from typing import cast

from inngest import Function, Inngest

from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    EmailDeliveryProvider,
    MessageRendererProvider,
    PushNotificationProvider,
    SecretEnvelopeProvider,
)
from shifu.communication.core.use_cases import (
    CancelCommunicationUseCase,
    DeleteAccountPushDataUseCase,
    DeliverCommunicationUseCase,
    DeliverStreakReminderUseCase,
    QueueStreakReminderUseCase,
)
from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
from shifu.communication.messaging.inngest.jobs import (
    CancelCommunicationJob,
    DeliverCommunicationJob,
    DeliverStreakReminderJob,
    PurgePushDataOnAccountDeletedJob,
)
from shifu.communication.providers.email import (
    FernetSecretEnvelopeProvider,
    GeneratedEmailMessageRenderer,
    ResendEmailDeliveryProvider,
    SmtpEmailDeliveryProvider,
)
from shifu.shared.constants import EnvironmentSettings
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
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
        message_renderer_provider: MessageRendererProvider | None = None,
        email_delivery_provider: EmailDeliveryProvider | None = None,
        push_notification_provider: PushNotificationProvider | None = None,
        streak_reminder_requested_event_name: str,
        account_deleted_event_name: str,
        telemetry_provider: TelemetryProvider,
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
        message_renderer_provider = (
            message_renderer_provider or GeneratedEmailMessageRenderer()
        )
        email_delivery_provider = email_delivery_provider or (
            CommunicationInngestMessaging._build_email_delivery_provider(
                settings,
                telemetry_provider,
            )
        )

        delivery_use_case = DeliverCommunicationUseCase(
            communication_database=communication_database,
            id_provider=id_provider,
            clock_provider=clock_provider,
            secret_envelope_provider=secret_envelope_provider,
            message_renderer_provider=message_renderer_provider,
            email_delivery_provider=email_delivery_provider,
        )
        cancellation_use_case = CancelCommunicationUseCase(
            communication_database=communication_database,
            clock_provider=clock_provider,
        )
        queue_streak_reminder_use_case = QueueStreakReminderUseCase(
            database=communication_database,
            id_provider=id_provider,
            clock_provider=clock_provider,
        )
        deliver_streak_reminder_use_case = DeliverStreakReminderUseCase(
            database=communication_database,
            id_provider=id_provider,
            clock_provider=clock_provider,
            push_notification_provider=push_notification_provider,
        )
        delete_account_push_data_use_case = DeleteAccountPushDataUseCase(
            database=communication_database,
            clock_provider=clock_provider,
        )
        return [
            cast(
                'Function[object]',
                DeliverCommunicationJob.handle(
                    inngest,
                    delivery_use_case,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                CancelCommunicationJob.handle(
                    inngest,
                    cancellation_use_case,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                DeliverStreakReminderJob.handle(
                    inngest,
                    queue_streak_reminder_use_case,
                    deliver_streak_reminder_use_case,
                    streak_reminder_requested_event_name=(
                        streak_reminder_requested_event_name
                    ),
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                PurgePushDataOnAccountDeletedJob.handle(
                    inngest,
                    delete_account_push_data_use_case,
                    account_deleted_event_name=account_deleted_event_name,
                    telemetry_provider=telemetry_provider,
                ),
            ),
        ]

    @staticmethod
    def _build_email_delivery_provider(
        settings: EnvironmentSettings,
        telemetry_provider: TelemetryProvider,
    ) -> EmailDeliveryProvider:
        if settings.email_provider == 'resend':
            if settings.resend_api_key is None or settings.resend_from is None:
                raise ValueError('Resend configuration is incomplete')

            return ResendEmailDeliveryProvider(
                api_key=settings.resend_api_key,
                sender=settings.resend_from,
                timeout_seconds=settings.email_timeout_seconds,
                telemetry_provider=telemetry_provider,
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
