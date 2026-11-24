from base64 import b32encode
from uuid import UUID

from shifu.communication.core.domain.entities import Communication
from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationType,
)
from shifu.communication.core.domain.structures import (
    AccountErasureOperationalAlertValues,
    CommunicationRequest,
)
from shifu.communication.core.use_cases.queue_communication_use_case import (
    QueueCommunicationUseCase,
)

_RECIPIENT = 'shifu.ctrlaltdel@gmail.com'


class QueueAccountErasureOperationalAlertUseCase:
    """Queue the fixed, PII-free notice once for one stable incident."""

    def __init__(self, queue_communication_use_case: QueueCommunicationUseCase) -> None:
        self._queue_communication_use_case = queue_communication_use_case

    def execute(
        self,
        values: AccountErasureOperationalAlertValues,
        incident_id: UUID,
    ) -> Communication:
        communication_id = b32encode(incident_id.bytes).decode('ascii')
        communication_id = communication_id.rstrip('=').lower()
        return self._queue_communication_use_case.execute(
            CommunicationRequest(
                communication_id=communication_id,
                identity_action_token_id=None,
                account_id=None,
                type=CommunicationType.ACCOUNT_ERASURE_ALERT,
                channel=CommunicationChannel.EMAIL,
                recipient_email=_RECIPIENT,
                recipient_name=None,
                message_values=values,
                idempotency_key=f'account-erasure-alert:{incident_id}',
                expires_at=None,
            )
        )
