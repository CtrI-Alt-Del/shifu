from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class SecretEnvelope:
    """Opaque encrypted message data owned by a provider adapter."""

    ciphertext: str
    key_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'ciphertext',
            NonEmptyText.create(
                self.ciphertext, error_type=InvalidCommunicationError
            ).value,
        )
        if self.key_id is not None:
            object.__setattr__(
                self,
                'key_id',
                NonEmptyText.create(
                    self.key_id, error_type=InvalidCommunicationError
                ).value,
            )


EncryptedMessageEnvelope = SecretEnvelope
