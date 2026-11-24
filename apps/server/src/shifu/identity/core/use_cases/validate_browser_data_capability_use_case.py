from hashlib import sha256

from shifu.identity.core.domain.structures import BrowserCapabilityStatus
from shifu.identity.core.interfaces import IdentityDatabase


class ValidateBrowserDataCapabilityUseCase:
    def __init__(self, identity_database: IdentityDatabase) -> None:
        self._identity_database = identity_database

    def execute(self, capability: str) -> BrowserCapabilityStatus:
        capability_hash = sha256(capability.encode('utf-8')).hexdigest()
        with self._identity_database.transaction() as repositories:
            status = repositories.account_browser_capabilities.find_status_by_hash(
                capability_hash
            )
        return BrowserCapabilityStatus(
            state='active' if status == 'active' else 'revoked'
        )
