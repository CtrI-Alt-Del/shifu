from datetime import datetime, timedelta
from typing import ClassVar

from shifu.communication.core.domain.entities import Communication, DeliveryAttempt
from shifu.communication.core.domain.enums import (
    CommunicationDeliveryState,
    CommunicationStatus,
)
from shifu.communication.core.domain.events import (
    CommunicationDeliveryStateChangedEvent,
    CommunicationDeliveryStateChangedPayload,
)
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures import DeliveryOutcome, EmailMessage
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    EmailDeliveryProvider,
    MessageRendererProvider,
    SecretEnvelopeProvider,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class DeliverCommunicationUseCase:
    """Deliver one persisted request with bounded, idempotent provider attempts."""

    MAX_ATTEMPTS: ClassVar[int] = 5
    RETRY_DELAYS: ClassVar[tuple[timedelta, ...]] = (
        timedelta(minutes=1),
        timedelta(minutes=5),
        timedelta(minutes=15),
        timedelta(minutes=60),
    )

    def __init__(
        self,
        communication_database: CommunicationDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        secret_envelope_provider: SecretEnvelopeProvider,
        message_renderer_provider: MessageRendererProvider,
        email_delivery_provider: EmailDeliveryProvider,
    ) -> None:
        self._communication_database = communication_database
        self._id_provider = id_provider
        self._clock_provider = clock_provider
        self._secret_envelope_provider = secret_envelope_provider
        self._message_renderer_provider = message_renderer_provider
        self._email_delivery_provider = email_delivery_provider

    def execute(self, communication_id: str) -> Communication | None:
        prepared = self._prepare_attempt(communication_id)
        if prepared is None:
            return self._settle_orphaned_attempt(communication_id)

        message, attempt_number, expires_at = prepared
        if expires_at is not None and self._clock_provider.now() >= expires_at:
            return self._expire_prepared_attempt(communication_id, attempt_number)
        outcome = self._email_delivery_provider.send(message)
        return self._settle_attempt(
            communication_id=communication_id,
            attempt_number=attempt_number,
            outcome=outcome,
        )

    def _prepare_attempt(
        self,
        communication_id: str,
    ) -> tuple[EmailMessage, int, datetime | None] | None:
        with self._communication_database.transaction() as repositories:
            communication = repositories.communications.find_by_id(communication_id)
            if communication is None:
                return None
            if communication.status is not CommunicationStatus.PENDING:
                return None
            identity_action_token_id = communication.identity_action_token_id
            if identity_action_token_id is None:
                raise InvalidCommunicationError
            attempted_at = self._clock_provider.now()
            if (
                communication.expires_at is not None
                and attempted_at >= communication.expires_at
            ):
                communication.reject(attempted_at, 'action_expired')
                repositories.communications.update(communication)
                repositories.events.add(
                    CommunicationDeliveryStateChangedEvent(
                        payload=CommunicationDeliveryStateChangedPayload(
                            communication_id=communication.id,
                            identity_action_token_id=identity_action_token_id,
                            state=CommunicationDeliveryState.EXPIRED,
                        )
                    )
                )
                return None
            if (
                communication.next_attempt_at is not None
                and communication.next_attempt_at > attempted_at
            ):
                return None
            if communication.attempt_count >= self.MAX_ATTEMPTS:
                return None

            attempt_number = communication.attempt_count + 1
            previous_attempt = repositories.delivery_attempts.find_by_communication_id_and_attempt_number(
                communication.id,
                attempt_number,
            )
            if previous_attempt is not None:
                return None

            communication.start_processing(attempted_at)
            attempt = DeliveryAttempt.create(
                id=self._id_provider.generate(),
                communication_id=communication.id,
                attempt_number=attempt_number,
                attempted_at=attempted_at,
            )
            repositories.delivery_attempts.add(attempt)

            message = self._create_message(communication)
            repositories.communications.update(communication)
            return message, attempt_number, communication.expires_at

    def _expire_prepared_attempt(
        self,
        communication_id: str,
        attempt_number: int,
    ) -> Communication | None:
        with self._communication_database.transaction() as repositories:
            communication = repositories.communications.find_by_id(communication_id)
            if communication is None:
                return None
            if communication.status is not CommunicationStatus.PROCESSING:
                return communication

            attempt = repositories.delivery_attempts.find_by_communication_id_and_attempt_number(
                communication.id,
                attempt_number,
            )
            identity_action_token_id = communication.identity_action_token_id
            if identity_action_token_id is None:
                raise InvalidCommunicationError

            expired_at = self._clock_provider.now()
            if attempt is not None:
                attempt.fail(expired_at, 'action_expired')
                repositories.delivery_attempts.update(attempt)
            communication.reject(expired_at, 'action_expired')
            repositories.communications.update(communication)
            repositories.events.add(
                CommunicationDeliveryStateChangedEvent(
                    payload=CommunicationDeliveryStateChangedPayload(
                        communication_id=communication.id,
                        identity_action_token_id=identity_action_token_id,
                        state=CommunicationDeliveryState.EXPIRED,
                    )
                )
            )
            return communication

    def _create_message(self, communication: Communication) -> EmailMessage:
        if communication.encrypted_content is not None:
            values = self._secret_envelope_provider.decrypt(
                communication.encrypted_content
            )
        elif communication.content is not None:
            values = communication.content
        else:
            raise InvalidCommunicationError
        if communication.recipient_email is None:
            raise InvalidCommunicationError
        rendered = self._message_renderer_provider.render(communication.type, values)
        return EmailMessage(
            idempotency_key=communication.idempotency_key,
            to=communication.recipient_email,
            subject=rendered.subject,
            html=rendered.html,
            text=rendered.text,
        )

    def _settle_attempt(
        self,
        *,
        communication_id: str,
        attempt_number: int,
        outcome: DeliveryOutcome,
    ) -> Communication | None:
        with self._communication_database.transaction() as repositories:
            communication = repositories.communications.find_by_id(communication_id)
            if communication is None:
                return None
            if communication.status is not CommunicationStatus.PROCESSING:
                return communication
            attempt = repositories.delivery_attempts.find_by_communication_id_and_attempt_number(
                communication.id,
                attempt_number,
            )
            if attempt is None:
                return communication

            identity_action_token_id = communication.identity_action_token_id
            if identity_action_token_id is None:
                raise InvalidCommunicationError
            settled_at = self._clock_provider.now()
            state: CommunicationDeliveryState
            if outcome.succeeded:
                attempt.succeed(settled_at, outcome.provider_message_id)
                communication.mark_sent(settled_at, outcome.provider_message_id)
                state = CommunicationDeliveryState.DELIVERED
            else:
                failure_code = outcome.failure_code or 'delivery_failed'
                attempt.fail(settled_at, failure_code)
                if outcome.retryable and attempt_number < self.MAX_ATTEMPTS:
                    next_attempt_at = settled_at + self.RETRY_DELAYS[attempt_number - 1]
                    if (
                        communication.expires_at is not None
                        and next_attempt_at >= communication.expires_at
                    ):
                        communication.mark_failed(
                            settled_at,
                            failure_code,
                            retryable=False,
                        )
                        state = CommunicationDeliveryState.EXPIRED
                    else:
                        communication.mark_failed(
                            settled_at,
                            failure_code,
                            retryable=True,
                            next_attempt_at=next_attempt_at,
                        )
                        state = CommunicationDeliveryState.TEMPORARY_FAILURE
                elif self._is_permanent_rejection(failure_code):
                    communication.reject(settled_at, failure_code)
                    state = CommunicationDeliveryState.PERMANENT_FAILURE
                else:
                    communication.mark_failed(
                        settled_at,
                        failure_code,
                        retryable=False,
                    )
                    state = (
                        CommunicationDeliveryState.EXHAUSTED
                        if outcome.retryable
                        else CommunicationDeliveryState.PERMANENT_FAILURE
                    )

            repositories.delivery_attempts.update(attempt)
            repositories.communications.update(communication)
            repositories.events.add(
                CommunicationDeliveryStateChangedEvent(
                    payload=CommunicationDeliveryStateChangedPayload(
                        communication_id=communication.id,
                        identity_action_token_id=identity_action_token_id,
                        state=state,
                    )
                )
            )
            return communication

    @staticmethod
    def _is_permanent_rejection(failure_code: str) -> bool:
        return failure_code.casefold() in {
            'rejected',
            'permanent_rejection',
            'bounced',
            'hard_bounce',
        }

    def _settle_orphaned_attempt(self, communication_id: str) -> Communication | None:
        with self._communication_database.transaction() as repositories:
            communication = repositories.communications.find_by_id(communication_id)
            if communication is None:
                return None
            if communication.status is not CommunicationStatus.PROCESSING:
                return communication

            attempt = repositories.delivery_attempts.find_by_communication_id_and_attempt_number(
                communication.id,
                communication.attempt_count,
            )
            identity_action_token_id = communication.identity_action_token_id
            if identity_action_token_id is None:
                raise InvalidCommunicationError

            settled_at = self._clock_provider.now()
            failure_code = 'delivery_outcome_unknown'
            if attempt is not None:
                attempt.fail(settled_at, failure_code)
            communication.mark_failed(
                settled_at,
                failure_code,
                retryable=False,
            )
            if attempt is not None:
                repositories.delivery_attempts.update(attempt)
            repositories.communications.update(communication)
            repositories.events.add(
                CommunicationDeliveryStateChangedEvent(
                    payload=CommunicationDeliveryStateChangedPayload(
                        communication_id=communication.id,
                        identity_action_token_id=identity_action_token_id,
                        state=CommunicationDeliveryState.PERMANENT_FAILURE,
                    )
                )
            )
            return communication
