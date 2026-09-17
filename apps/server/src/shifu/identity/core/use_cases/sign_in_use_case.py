from shifu.identity.core.domain.enums import AccountAccess, AccountStatus
from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.identity.core.domain.structures import (
    AccountProfile,
    AuthCredentials,
    Authentication,
)
from shifu.identity.core.interfaces import IdentityDatabase, PasswordHashingProvider


class SignInUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        password_hashing_provider: PasswordHashingProvider,
    ) -> None:
        self._identity_database = identity_database
        self._password_hashing_provider = password_hashing_provider

    def execute(self, credentials: AuthCredentials) -> Authentication:
        email = credentials.email.strip()
        with self._identity_database.transaction() as repositories:
            account = repositories.accounts.find_non_deleted_by_email(email)

            if account is None:
                raise InvalidCredentialsError

            if not self._password_hashing_provider.verify(
                credentials.password,
                account.password_hash,
            ):
                raise InvalidCredentialsError

            if account.status not in {
                AccountStatus.ACTIVE,
                AccountStatus.PENDING_CONFIRMATION,
            }:
                raise InvalidCredentialsError

            access = (
                AccountAccess.PROTECTED
                if account.status is AccountStatus.ACTIVE
                else AccountAccess.ACTIVATION_ONLY
            )
            return Authentication(
                profile=AccountProfile(
                    account_id=account.id,
                    display_name=account.display_name,
                    email=account.email,
                    time_zone=account.time_zone,
                    status=account.status,
                    created_at=account.created_at,
                    confirmed_at=account.confirmed_at,
                ),
                access=access,
                access_version=account.access_version,
            )
