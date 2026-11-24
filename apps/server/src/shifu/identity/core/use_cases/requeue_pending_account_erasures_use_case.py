from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from shifu.identity.core.domain.events import (
    AccountErasureOperationalAlertRequestedEvent,
    AccountErasureOperationalAlertRequestedPayload,
    AccountErasureRequestedEvent,
    AccountErasureRequestedPayload,
)
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.shared.core.interfaces import ClockProvider


class RequeuePendingAccountErasuresUseCase:
    RETENTION = timedelta(days=30)
    BATCH_SIZE = 100

    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider

    def execute(self) -> int:
        now = self._clock_provider.now()
        with self._identity_database.transaction() as repositories:
            pending = repositories.account_erasures.find_pending(limit=self.BATCH_SIZE)
            for erasure_id in pending:
                repositories.events.add(
                    AccountErasureRequestedEvent(
                        payload=AccountErasureRequestedPayload(
                            erasure_id=str(erasure_id)
                        )
                    )
                )
            overdue_participants = (
                repositories.account_erasures.find_overdue_pending_participants(
                    as_of=now,
                    limit=self.BATCH_SIZE,
                )
            )
            for participant in overdue_participants:
                incident_id = uuid5(
                    NAMESPACE_URL,
                    (
                        'shifu:account-erasure-overdue:v1:'
                        f'{participant.erasure_id}:{participant.module}:'
                        f'{participant.due_at.isoformat()}'
                    ),
                )
                repositories.events.add(
                    AccountErasureOperationalAlertRequestedEvent(
                        payload=AccountErasureOperationalAlertRequestedPayload(
                            incident_id=str(incident_id),
                            erasure_id=str(participant.erasure_id),
                            module=participant.module,
                            failure_code='erasure_deadline_exceeded',
                            closed_at=participant.closed_at,
                            due_at=participant.due_at,
                        )
                    )
                )
            repositories.account_erasures.remove_completed_before(
                now - self.RETENTION,
                limit=self.BATCH_SIZE,
            )
            repositories.external_effect_receipts.remove_reconciliations_before(
                now - self.RETENTION,
                limit=self.BATCH_SIZE,
            )
        return len(pending)
