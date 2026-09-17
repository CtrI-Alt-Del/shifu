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
from shifu.communication.core.domain.structures import MessageContent
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import normalize_email, require_non_empty


@entity
class Communication:
    id: str
    account_id: str | None
    type: CommunicationType
    channel: CommunicationChannel
    recipient_email: str
    recipient_name: str | None
    content: MessageContent
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

    def __post_init__(self) -> None:
        self.recipient_email = normalize_email(
            self.recipient_email,
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
        recipient_email: str,
        recipient_name: str | None,
        content: MessageContent,
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
        )

    def start_processing(self, processed_at: datetime) -> None:
        if self.status is not CommunicationStatus.PENDING:
            raise CommunicationTransitionError
        self.status = CommunicationStatus.PROCESSING
        self.attempt_count += 1
        self.updated_at = processed_at

    def mark_sent(self, sent_at: datetime, provider_message_id: str) -> None:
        if self.status is not CommunicationStatus.PROCESSING:
            raise CommunicationTransitionError
        self.status = CommunicationStatus.SENT
        self.sent_at = sent_at
        self.provider_message_id = provider_message_id
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
        self.updated_at = rejected_at
