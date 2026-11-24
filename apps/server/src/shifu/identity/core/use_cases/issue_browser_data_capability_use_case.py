from hashlib import sha256
import secrets

from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.identity.core.interfaces import IdentityDatabase


class IssueBrowserDataCapabilityUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider

    def execute(self, user: AuthenticatedUser) -> str:
        capability = secrets.token_urlsafe(32)
        capability_hash = sha256(capability.encode('utf-8')).hexdigest()
        with self._identity_database.transaction() as repositories:
            repositories.account_browser_capabilities.add(
                account_id=user.account_id,
                capability_hash=capability_hash,
                created_at=self._clock_provider.now(),
            )
        return capability
