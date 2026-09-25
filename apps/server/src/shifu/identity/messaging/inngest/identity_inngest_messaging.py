from typing import cast

from inngest import Function, Inngest

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.core.use_cases import (
    ExpireUnconfirmedAccountsUseCase,
    RecordCommunicationDeliveryStateUseCase,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.messaging.inngest.jobs import (
    ExpireUnconfirmedAccountJob,
    FanOutUnconfirmedAccountExpiryJob,
    LogMainPageEnteredJob,
    RecordCommunicationDeliveryStateJob,
)
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider


class IdentityInngestMessaging:
    """Declare the Inngest functions owned by Identity."""

    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        identity_database: IdentityDatabase | None = None,
        clock_provider: ClockProvider | None = None,
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
        return [
            cast('Function[object]', LogMainPageEnteredJob.handle(inngest)),
            cast(
                'Function[object]',
                FanOutUnconfirmedAccountExpiryJob.handle(
                    inngest,
                    expiry_use_case,
                ),
            ),
            cast(
                'Function[object]',
                ExpireUnconfirmedAccountJob.handle(inngest, expiry_use_case),
            ),
            cast(
                'Function[object]',
                RecordCommunicationDeliveryStateJob.handle(
                    inngest,
                    delivery_state_use_case,
                ),
            ),
        ]
