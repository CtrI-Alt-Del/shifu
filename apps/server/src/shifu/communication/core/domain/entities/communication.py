from datetime import datetime

from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationStatus,
    CommunicationType,
)
from shifu.communication.core.domain.errors import (
    CommunicationTransitionError,
    InvalidCommunicationError,
)
from shifu.communication.core.domain.structures import MessageContent, SecretEnvelope
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import normalize_email, require_non_empty


@entity
class Communication:
    id: str
    account_id: str | None
    type: CommunicationType
    channel: CommunicationChannel
    recipient_email: str | None
    recipient_name: str | None
    content: MessageContent | None
    status: CommunicationStatus
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None = None
    failed_at: datetime | None = None
    failure_code: str | None = None
    provider_message_id: str | None = None
    attempt_count: int = 0
    next_attempt_at: datetime | None = None
    identity_confirmation_id: str | None = None
    encrypted_content: SecretEnvelope | None = None
    redacted_at: datetime | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.id, InvalidCommunicationError)
        try:
            self.type = CommunicationType(self.type)
            self.channel = CommunicationChannel(self.channel)
            self.status = CommunicationStatus(self.status)
        except ValueError:
            raise InvalidCommunicationError from None
        if self.recipient_email is not None:
            self.recipient_email = normalize_email(
                self.recipient_email,
                InvalidCommunicationError,
            )
        if self.identity_confirmation_id is not None:
            self.identity_confirmation_id = require_non_empty(
                self.identity_confirmation_id,
                InvalidCommunicationError,
            )
        self.idempotency_key = require_non_empty(
            self.idempotency_key,
            InvalidCommunicationError,
        )
        if self.attempt_count < 0:
            raise InvalidCommunicationError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str | None,
        type: CommunicationType,
        channel: CommunicationChannel,
        recipient_email: str | None,
        recipient_name: str | None,
        content: MessageContent | None,
        status: CommunicationStatus,
        idempotency_key: str,
        created_at: datetime,
        updated_at: datetime,
        sent_at: datetime | None = None,
        failed_at: datetime | None = None,
        failure_code: str | None = None,
        provider_message_id: str | None = None,
        attempt_count: int = 0,
        next_attempt_at: datetime | None = None,
        identity_confirmation_id: str | None = None,
        encrypted_content: SecretEnvelope | None = None,
        redacted_at: datetime | None = None,
    ) -> 'Communication':
        return cls(
            id=id,
            account_id=account_id,
            type=type,
            channel=channel,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            content=content,
            status=status,
            idempotency_key=idempotency_key,
            created_at=created_at,
            updated_at=updated_at,
            sent_at=sent_at,
            failed_at=failed_at,
            failure_code=failure_code,
            provider_message_id=provider_message_id,
            attempt_count=attempt_count,
            next_attempt_at=next_attempt_at,
            identity_confirmation_id=identity_confirmation_id,
            encrypted_content=encrypted_content,
            redacted_at=redacted_at,
        )

    def start_processing(self, processed_at: datetime) -> None:
        if self.status is not CommunicationStatus.PENDING:
            raise CommunicationTransitionError
        self.status = CommunicationStatus.PROCESSING
        self.attempt_count += 1
        self.next_attempt_at = None
        self.updated_at = processed_at

    def mark_sent(
        self,
        sent_at: datetime,
        provider_message_id: str | None,
    ) -> None:
        if self.status is not CommunicationStatus.PROCESSING:
            raise CommunicationTransitionError
        self.status = CommunicationStatus.SENT
        self.sent_at = sent_at
        self.provider_message_id = provider_message_id
        self.failure_code = None
        self.next_attempt_at = None
        self.updated_at = sent_at

    def mark_failed(
        self,
        failed_at: datetime,
        failure_code: str,
        retryable: bool,
        next_attempt_at: datetime | None = None,
    ) -> None:
        if self.status is not CommunicationStatus.PROCESSING:
            raise CommunicationTransitionError
        self.failure_code = require_non_empty(failure_code, InvalidCommunicationError)
        self.failed_at = failed_at
        self.updated_at = failed_at
        self.next_attempt_at = next_attempt_at
        self.status = (
            CommunicationStatus.PENDING
            if retryable
            else CommunicationStatus.PERMANENTLY_FAILED
        )

    def reject(self, rejected_at: datetime, failure_code: str) -> None:
        if self.status not in {
            CommunicationStatus.PENDING,
            CommunicationStatus.PROCESSING,
        }:
            raise CommunicationTransitionError
        self.status = CommunicationStatus.REJECTED
        self.failure_code = require_non_empty(failure_code, InvalidCommunicationError)
        self.failed_at = rejected_at
        self.next_attempt_at = None
        self.updated_at = rejected_at

    def cancel(self, cancelled_at: datetime) -> None:
        if self.status not in {
            CommunicationStatus.PENDING,
            CommunicationStatus.PROCESSING,
        }:
            raise CommunicationTransitionError
        self.status = CommunicationStatus.CANCELLED
        self.next_attempt_at = None
        self.updated_at = cancelled_at

    def redact(self, redacted_at: datetime) -> None:
        """Remove active account and message associations without restoring state."""

        self.account_id = None
        self.recipient_email = None
        self.recipient_name = None
        self.identity_confirmation_id = None
        self.content = None
        self.encrypted_content = None
        self.provider_message_id = None
        self.redacted_at = redacted_at
        self.updated_at = redacted_at

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            CommunicationStatus.SENT,
            CommunicationStatus.PERMANENTLY_FAILED,
            CommunicationStatus.REJECTED,
            CommunicationStatus.CANCELLED,
        }

    @property
    def is_redacted(self) -> bool:
        return (
            self.account_id is None
            and self.recipient_email is None
            and self.identity_confirmation_id is None
            and self.content is None
            and self.encrypted_content is None
        )
