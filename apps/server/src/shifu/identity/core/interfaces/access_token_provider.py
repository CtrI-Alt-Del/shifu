from datetime import datetime
from typing import Protocol

from shifu.identity.core.domain.enums import AccountAccess
from shifu.identity.core.domain.structures import IssuedAccessToken


class AccessTokenProvider(Protocol):
    def issue(
        self,
        *,
        account_id: str,
        access_version: int,
        access: AccountAccess,
        issued_at: datetime,
    ) -> IssuedAccessToken:
        """Issue access using a timezone-aware UTC issuance time."""
        ...
