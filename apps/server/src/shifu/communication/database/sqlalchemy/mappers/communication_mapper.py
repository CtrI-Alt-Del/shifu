from typing import cast

from shifu.communication.core.domain.entities import Communication
from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationStatus,
    CommunicationType,
)
from shifu.communication.core.domain.structures import MessageContent
from shifu.communication.core.domain.structures import SecretEnvelope
from shifu.communication.database.sqlalchemy.models import CommunicationModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


class CommunicationMapper:
    @staticmethod
    def to_domain(model: CommunicationModel) -> Communication:
        return Communication(
            id=model.id,
            account_id=model.account_id,
            type=CommunicationType(model.type),
            channel=CommunicationChannel(model.channel),
            recipient_email=model.recipient_email,
            recipient_name=model.recipient_name,
            content=cast(
                'MessageContent | None',
                (
                    Serialization.deserialize_value(model.content, MessageContent)
                    if model.content is not None
                    else None
                ),
            ),
            status=CommunicationStatus(model.status),
            idempotency_key=model.idempotency_key,
            created_at=model.created_at,
            updated_at=model.updated_at,
            sent_at=model.sent_at,
            failed_at=model.failed_at,
            failure_code=model.failure_code,
            provider_message_id=model.provider_message_id,
            attempt_count=model.attempt_count,
            next_attempt_at=model.next_attempt_at,
            identity_confirmation_id=model.identity_confirmation_id,
            encrypted_content=cast(
                'SecretEnvelope | None',
                (
                    Serialization.deserialize_value(
                        model.encrypted_content,
                        SecretEnvelope,
                    )
                    if model.encrypted_content is not None
                    else None
                ),
            ),
            redacted_at=model.redacted_at,
        )

    @staticmethod
    def to_model(communication: Communication) -> CommunicationModel:
        return CommunicationModel(
            id=communication.id,
            account_id=communication.account_id,
            type=communication.type.value,
            channel=communication.channel.value,
            recipient_email=communication.recipient_email,
            recipient_name=communication.recipient_name,
            content=cast(
                'dict[str, object] | None',
                Serialization.serialize_value(communication.content),
            ),
            status=communication.status.value,
            idempotency_key=communication.idempotency_key,
            created_at=communication.created_at,
            updated_at=communication.updated_at,
            sent_at=communication.sent_at,
            failed_at=communication.failed_at,
            failure_code=communication.failure_code,
            provider_message_id=communication.provider_message_id,
            attempt_count=communication.attempt_count,
            next_attempt_at=communication.next_attempt_at,
            identity_confirmation_id=communication.identity_confirmation_id,
            encrypted_content=cast(
                'dict[str, object] | None',
                Serialization.serialize_value(communication.encrypted_content),
            ),
            redacted_at=communication.redacted_at,
        )
