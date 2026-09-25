from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


@structure
class SecretEnvelope:
    """Opaque encrypted message data owned by a provider adapter."""

    ciphertext: str
    key_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'ciphertext',
            require_non_empty(self.ciphertext, InvalidCommunicationError),
        )
        if self.key_id is not None:
            object.__setattr__(
                self,
                'key_id',
                require_non_empty(self.key_id, InvalidCommunicationError),
            )


EncryptedMessageEnvelope = SecretEnvelope
