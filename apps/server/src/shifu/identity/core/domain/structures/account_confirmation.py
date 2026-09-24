from shifu.identity.core.domain.structures.account_profile import AccountProfile
from shifu.identity.core.domain.enums import AccountConfirmationResultStatus
from shifu.shared.core.domain.structures import structure


@structure
class AccountConfirmationResult:
    result: AccountConfirmationResultStatus
    profile: AccountProfile | None = None
    access_version: int | None = None
