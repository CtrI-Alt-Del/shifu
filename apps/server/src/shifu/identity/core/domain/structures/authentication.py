from datetime import datetime

from shifu.identity.core.domain.enums import AccountAccess
from shifu.identity.core.domain.structures.account_profile import AccountProfile
from shifu.shared.core.domain.structures import structure


@structure
class Authentication:
    token: str
    profile: AccountProfile
    access: AccountAccess
    expires_at: datetime
