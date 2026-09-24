import hashlib
import secrets


class PendingConfirmationHandleProvider:
    """Create opaque, server-side pending-flow handles."""

    def generate(self) -> str:
        return secrets.token_urlsafe(32)

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
