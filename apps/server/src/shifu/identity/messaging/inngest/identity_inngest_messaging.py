from typing import cast

from inngest import Function, Inngest

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.core.use_cases import (
    CloseBffIdentityForAccountErasureUseCase,
    ExpireUnconfirmedAccountsUseCase,
    RecordCommunicationDeliveryStateUseCase,
    RequeuePendingAccountErasuresUseCase,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.providers.account_erasure import (
    HttpAccountErasureBffProvider,
    SqlalchemyAccountErasureProvider,
)
from shifu.identity.messaging.inngest.jobs import (
    CloseBffIdentityOnAccountErasureJob,
    ExpireUnconfirmedAccountJob,
    FanOutUnconfirmedAccountExpiryJob,
    LogMainPageEnteredJob,
    RecordCommunicationDeliveryStateJob,
    SweepAccountErasuresJob,
)
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider


class IdentityInngestMessaging:
    """Declare the Inngest functions owned by Identity."""

    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        identity_database: IdentityDatabase | None = None,
        clock_provider: ClockProvider | None = None,
        telemetry_provider: TelemetryProvider,
    ) -> list[Function[object]]:
        identity_database = identity_database or SqlalchemyIdentityDatabase()
        clock_provider = clock_provider or SystemClockProvider()
        expiry_use_case = ExpireUnconfirmedAccountsUseCase(
            identity_database=identity_database,
            clock_provider=clock_provider,
        )
        delivery_state_use_case = RecordCommunicationDeliveryStateUseCase(
            identity_database=identity_database,
            clock_provider=clock_provider,
        )
        erasure_sweep_use_case = RequeuePendingAccountErasuresUseCase(
            identity_database,
            clock_provider,
        )
        close_bff_identity_use_case = CloseBffIdentityForAccountErasureUseCase(
            target_provider=SqlalchemyAccountErasureProvider(
                identity_database,
                clock_provider,
            ),
            bff_provider=HttpAccountErasureBffProvider(
                base_url=ENVIRONMENT.bff_base_url,
                shared_secret=ENVIRONMENT.bff_shared_secret,
                timeout_seconds=ENVIRONMENT.email_timeout_seconds,
            ),
        )
        return [
            cast(
                'Function[object]',
                LogMainPageEnteredJob.handle(
                    inngest,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                FanOutUnconfirmedAccountExpiryJob.handle(
                    inngest,
                    expiry_use_case,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                ExpireUnconfirmedAccountJob.handle(
                    inngest,
                    expiry_use_case,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                RecordCommunicationDeliveryStateJob.handle(
                    inngest,
                    delivery_state_use_case,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                SweepAccountErasuresJob.handle(
                    inngest,
                    erasure_sweep_use_case,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                CloseBffIdentityOnAccountErasureJob.handle(
                    inngest,
                    close_bff_identity_use_case,
                    telemetry_provider=telemetry_provider,
                ),
            ),
        ]
