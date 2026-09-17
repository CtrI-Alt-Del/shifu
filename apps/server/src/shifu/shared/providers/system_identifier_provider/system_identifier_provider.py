"""System-backed ULID identifier provider."""

from datetime import UTC, datetime
import secrets

from shifu.shared.core.interfaces import IdentifierProvider


_ULID_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'


class SystemIdentifierProvider(IdentifierProvider):
    def generate(self) -> str:
        timestamp = int(datetime.now(UTC).timestamp() * 1000)
        encoded_timestamp = self._encode_base32(timestamp, 10)
        random_part = ''.join(secrets.choice(_ULID_ALPHABET) for _ in range(16))
        return encoded_timestamp + random_part

    def _encode_base32(self, value: int, length: int) -> str:
        characters: list[str] = []
        for _ in range(length):
            value, remainder = divmod(value, 32)
            characters.append(_ULID_ALPHABET[remainder])
        return ''.join(reversed(characters))
