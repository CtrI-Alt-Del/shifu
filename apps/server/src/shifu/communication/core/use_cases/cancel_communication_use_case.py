from shifu.communication.core.domain.entities import Communication
from shifu.communication.core.domain.enums import (
    CommunicationCancellationReason,
    CommunicationDeliveryState,
    CommunicationStatus,
)
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.events import (
    CommunicationDeliveryStateChangedEvent,
    CommunicationDeliveryStateChangedPayload,
)
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
)
from shifu.shared.core.domain.structures import NonEmptyText
from shifu.shared.core.interfaces import ClockProvider


class CancelCommunicationUseCase:
    """Apply an ID-pair cancellation without importing the requesting module."""

    def __init__(
        self,
        communication_database: CommunicationDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._communication_database = communication_database
        self._clock_provider = clock_provider

    def execute(
        self,
        communication_id: str,
        identity_action_token_id: str,
        reason: CommunicationCancellationReason | str,
    ) -> bool:
        communication_id = NonEmptyText.create(
            communication_id,
            error_type=InvalidCommunicationError,
        ).value
        identity_action_token_id = NonEmptyText.create(
            identity_action_token_id,
            error_type=InvalidCommunicationError,
        ).value
        try:
            cancellation_reason = CommunicationCancellationReason(reason)
        except ValueError:
            raise InvalidCommunicationError from None

        with self._communication_database.transaction() as repositories:
            communication = self._find_correlated_communication(
                repositories,
                communication_id,
                identity_action_token_id,
            )
            if communication is None:
                return False
            return self._apply_cancellation(
                repositories,
                communication,
                identity_action_token_id,
                cancellation_reason,
            )

    @staticmethod
    def _find_correlated_communication(
        repositories: CommunicationDatabaseRepositories,
        communication_id: str,
        identity_action_token_id: str,
    ) -> Communication | None:
        communication = repositories.communications.find_by_id(communication_id)
        if not isinstance(communication, Communication):
            return None
        if communication.identity_action_token_id != identity_action_token_id:
            return None
        return communication

    def _apply_cancellation(
        self,
        repositories: CommunicationDatabaseRepositories,
        communication: Communication,
        identity_action_token_id: str,
        cancellation_reason: CommunicationCancellationReason,
    ) -> bool:
        if communication.status is CommunicationStatus.CANCELLED and (
            cancellation_reason is not CommunicationCancellationReason.EXPIRED
            or communication.is_redacted
        ):
            return False

        now = self._clock_provider.now()
        should_cancel = communication.status in {
            CommunicationStatus.PENDING,
            CommunicationStatus.PROCESSING,
        }
        if cancellation_reason is CommunicationCancellationReason.EXPIRED:
            if should_cancel:
                communication.cancel(now)
            communication.redact(now)
            repositories.communications.update(communication)
            repositories.delivery_attempts.redact_by_communication_id(communication.id)
            if should_cancel:
                self._add_cancelled_event(
                    repositories,
                    communication,
                    identity_action_token_id,
                )
            return True

        if not should_cancel:
            return False
        communication.cancel(now)
        repositories.communications.update(communication)
        self._add_cancelled_event(
            repositories,
            communication,
            identity_action_token_id,
        )
        return True

    @staticmethod
    def _add_cancelled_event(
        repositories: CommunicationDatabaseRepositories,
        communication: Communication,
        identity_action_token_id: str,
    ) -> None:
        repositories.events.add(
            CommunicationDeliveryStateChangedEvent(
                payload=CommunicationDeliveryStateChangedPayload(
                    communication_id=communication.id,
                    identity_action_token_id=identity_action_token_id,
                    state=CommunicationDeliveryState.CANCELLED,
                )
            )
        )
