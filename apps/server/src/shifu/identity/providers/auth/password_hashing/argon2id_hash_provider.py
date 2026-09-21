from argon2 import PasswordHasher
from argon2.exceptions import HashingError, InvalidHashError, VerificationError


class Argon2idHashProvider:
    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (HashingError, InvalidHashError, VerificationError):
            return False
