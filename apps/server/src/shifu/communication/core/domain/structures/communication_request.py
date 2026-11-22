from datetime import datetime

from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationType,
)
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures.account_erasure_operational_alert_values import (
    AccountErasureOperationalAlertValues,
)
from shifu.communication.core.domain.structures.message_content import MessageContent
from shifu.communication.core.domain.structures.message_template_values import (
    MessageTemplateValues,
)
from shifu.shared.core.domain.structures import EmailAddress, NonEmptyText, structure


@structure
class CommunicationRequest:
    communication_id: str
    identity_action_token_id: str | None
    account_id: str | None
    type: CommunicationType
    channel: CommunicationChannel
    recipient_email: str
    recipient_name: str | None
    content: MessageContent | None = None
    message_values: (
        MessageTemplateValues | AccountErasureOperationalAlertValues | None
    ) = None
    idempotency_key: str = ''
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        self._normalize_communication_id()
        message_type = self._normalize_type_and_channel()
        self._validate_identity_fields(message_type)
        self._normalize_recipient()
        self._validate_message_values(message_type)
        self._normalize_idempotency_key()

    def _normalize_communication_id(self) -> None:
        object.__setattr__(
            self,
            'communication_id',
            NonEmptyText.create(
                self.communication_id, error_type=InvalidCommunicationError
            ).value,
        )

    def _normalize_type_and_channel(self) -> CommunicationType:
        try:
            message_type = CommunicationType(self.type)
            channel = CommunicationChannel(self.channel)
        except ValueError:
            raise InvalidCommunicationError from None
        if channel is not CommunicationChannel.EMAIL:
            raise InvalidCommunicationError
        object.__setattr__(self, 'type', message_type)
        object.__setattr__(self, 'channel', channel)

        return message_type

    def _validate_identity_fields(self, message_type: CommunicationType) -> None:
        if message_type is CommunicationType.ACCOUNT_ERASURE_ALERT:
            if (
                self.identity_action_token_id is not None
                or self.account_id is not None
                or self.recipient_name is not None
                or self.expires_at is not None
                or self.content is not None
                or not isinstance(
                    self.message_values, AccountErasureOperationalAlertValues
                )
            ):
                raise InvalidCommunicationError
        else:
            if self.identity_action_token_id is None or self.account_id is None:
                raise InvalidCommunicationError
            object.__setattr__(
                self,
                'identity_action_token_id',
                NonEmptyText.create(
                    self.identity_action_token_id,
                    error_type=InvalidCommunicationError,
                ).value,
            )

    def _normalize_recipient(self) -> None:
        object.__setattr__(
            self,
            'recipient_email',
            EmailAddress.create(
                self.recipient_email, error_type=InvalidCommunicationError
            ).value,
        )

    def _validate_message_values(self, message_type: CommunicationType) -> None:
        if self.content is None and self.message_values is None:
            raise InvalidCommunicationError
        if message_type is CommunicationType.ACCOUNT_ERASURE_ALERT:
            if self.recipient_email != 'shifu.ctrlaltdel@gmail.com':
                raise InvalidCommunicationError
        elif self.message_values is not None and not isinstance(
            self.message_values, MessageTemplateValues
        ):
            raise InvalidCommunicationError
        if isinstance(self.message_values, MessageTemplateValues):
            if message_type is CommunicationType.ACCOUNT_CONFIRMATION and (
                self.message_values.display_name is None
            ):
                raise InvalidCommunicationError
            if message_type is CommunicationType.PASSWORD_RECOVERY and (
                self.message_values.display_name is not None
            ):
                raise InvalidCommunicationError

    def _normalize_idempotency_key(self) -> None:
        object.__setattr__(
            self,
            'idempotency_key',
            NonEmptyText.create(
                self.idempotency_key or self.communication_id,
                error_type=InvalidCommunicationError,
            ).value,
        )
