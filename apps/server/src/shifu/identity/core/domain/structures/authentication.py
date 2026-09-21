from shifu.identity.core.domain.enums import AccountAccess
from shifu.identity.core.domain.structures.account_profile import AccountProfile
from shifu.shared.core.domain.structures import structure


@structure
class Authentication:
    profile: AccountProfile
    access: AccountAccess
    access_version: int
