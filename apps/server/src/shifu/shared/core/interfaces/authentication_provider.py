from typing import Protocol

from shifu.shared.core.domain.structures import AuthenticatedUser


class AuthenticationProvider(Protocol):
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        """Authenticate valid protected access for a currently active account.

        Raise AuthorizationError for an invalid, expired, revoked, activation-only,
        or stale-version token, or when the current account is not active.
        """
        ...
