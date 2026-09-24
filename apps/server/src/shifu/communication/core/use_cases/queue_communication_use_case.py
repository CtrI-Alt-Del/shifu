from shifu.communication.core.domain.entities import Communication
from shifu.communication.core.domain.events import (
    CommunicationQueuedEvent,
    CommunicationQueuedPayload,
)
from shifu.communication.core.domain.enums import CommunicationStatus
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures import CommunicationRequest
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    SecretEnvelopeProvider,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class QueueCommunicationUseCase:
    """Persist one controlled communication request and its ID-only outbox event."""

    def __init__(
        self,
        communication_database: CommunicationDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        secret_envelope_provider: SecretEnvelopeProvider,
    ) -> None:
        self._communication_database = communication_database
        # The request already owns the communication identity.  The identifier
        # port remains explicit so a transaction adapter can use the same core
        # dependency set for event/attempt identities without generating a new
        # communication identity here.
        self._id_provider = id_provider
        self._clock_provider = clock_provider
        self._secret_envelope_provider = secret_envelope_provider

    def execute(self, request: CommunicationRequest) -> Communication:
        with self._communication_database.transaction() as repositories:
            existing = repositories.communications.find_by_id(request.communication_id)
            if existing is None:
                existing = repositories.communications.find_by_idempotency_key(
                    request.idempotency_key
                )
            if existing is not None:
                self._validate_idempotent_replay(request, existing)
                return existing

            values = request.message_values or request.content
            if values is None:
                raise InvalidCommunicationError

            encrypted_content = self._secret_envelope_provider.encrypt(values)
            created_at = self._clock_provider.now()
            communication = Communication.create(
                id=request.communication_id,
                account_id=request.account_id,
                type=request.type,
                channel=request.channel,
                recipient_email=request.recipient_email,
                recipient_name=request.recipient_name,
                content=None,
                status=CommunicationStatus.PENDING,
                idempotency_key=request.idempotency_key,
                created_at=created_at,
                updated_at=created_at,
                identity_confirmation_id=request.identity_confirmation_id,
                encrypted_content=encrypted_content,
            )
            repositories.communications.add(communication)
            repositories.events.add(
                CommunicationQueuedEvent(
                    payload=CommunicationQueuedPayload(
                        communication_id=communication.id,
                    )
                )
            )
            return communication

    @staticmethod
    def _validate_idempotent_replay(
        request: CommunicationRequest,
        existing: Communication,
    ) -> None:
        if existing.id != request.communication_id:
            raise InvalidCommunicationError
        if existing.identity_confirmation_id != request.identity_confirmation_id:
            raise InvalidCommunicationError
        if existing.idempotency_key != request.idempotency_key:
            raise InvalidCommunicationError
