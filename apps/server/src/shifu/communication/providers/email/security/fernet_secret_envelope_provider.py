from __future__ import annotations

import json
from typing import cast

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures import (
    MessageContent,
    MessageTemplateValues,
    SecretEnvelope,
)
from shifu.shared.database.sqlalchemy.serialization import Serialization


class FernetSecretEnvelopeProvider:
    """Encrypt retryable Communication values using an ordered Fernet key ring."""

    def __init__(self, keys: tuple[str, ...] | list[str]) -> None:
        normalized_keys = tuple(key.strip() for key in keys if key.strip())
        if not normalized_keys:
            raise ValueError('At least one Communication encryption key is required')
        try:
            fernets = [Fernet(key.encode('ascii')) for key in normalized_keys]
        except (ValueError, UnicodeEncodeError) as error:
            raise ValueError('Communication encryption keys are invalid') from error
        self._fernet = MultiFernet(fernets)

    def encrypt(
        self,
        values: MessageContent | MessageTemplateValues,
    ) -> SecretEnvelope:
        serialized = Serialization.serialize_value(values)
        if not isinstance(serialized, dict):
            raise InvalidCommunicationError
        plaintext = json.dumps(
            serialized,
            ensure_ascii=False,
            separators=(',', ':'),
            sort_keys=True,
        ).encode('utf-8')
        return SecretEnvelope(
            ciphertext=self._fernet.encrypt(plaintext).decode('ascii'),
            key_id='0',
        )

    def decrypt(
        self, envelope: SecretEnvelope
    ) -> MessageContent | MessageTemplateValues:
        try:
            raw_value = json.loads(
                self._fernet.decrypt(envelope.ciphertext.encode('ascii')).decode(
                    'utf-8'
                )
            )
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise InvalidCommunicationError from None
        if not isinstance(raw_value, dict):
            raise InvalidCommunicationError
        value = cast('dict[str, object]', raw_value)
        if 'display_name' in value and 'action_url' in value:
            return cast(
                'MessageTemplateValues',
                Serialization.deserialize_value(value, MessageTemplateValues),
            )
        if 'subject' in value and 'html' in value:
            return cast(
                'MessageContent',
                Serialization.deserialize_value(value, MessageContent),
            )
        raise InvalidCommunicationError
