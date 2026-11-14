from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.core.domain.structures import AccountProfile
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser


class GetAccountProfileUseCase:
    def __init__(self, identity_database: IdentityDatabase) -> None:
        self._identity_database: IdentityDatabase = identity_database

    def execute(self, user: AuthenticatedUser) -> AccountProfile:
        with self._identity_database.transaction() as repositories:
            account = repositories.accounts.find_by_id(user.account_id)
            if (
                account is None
                or not user.session_id
                or user.token_access_version is None
                or user.account_access_version != account.access_version
                or not account.accepts_access(
                    user.session_id, user.token_access_version
                )
            ):
                raise AuthorizationError
            return AccountProfile(
                account_id=account.id,
                display_name=account.display_name,
                email=account.email,
                time_zone=account.time_zone,
                status=account.status,
                created_at=account.created_at,
                confirmed_at=account.confirmed_at,
            )
