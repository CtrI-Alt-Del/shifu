from shifu.identity.core.domain.enums import (
    AccountActionTokenCancellationReason,
    AccountActionTokenType,
)
from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.identity.core.domain.events import (
    AccountActionTokenCancelledEvent,
    AccountActionTokenCancelledPayload,
)
from shifu.identity.core.domain.structures import PasswordChangeRequest
from shifu.identity.core.interfaces import IdentityDatabase, PasswordHashingProvider
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider


class ChangePasswordUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        password_hashing_provider: PasswordHashingProvider,
    ) -> None:
        self._identity_database: IdentityDatabase = identity_database
        self._clock_provider: ClockProvider = clock_provider
        self._password_hashing_provider: PasswordHashingProvider = (
            password_hashing_provider
        )

    def execute(self, user: AuthenticatedUser, request: PasswordChangeRequest) -> None:
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
            if not self._password_hashing_provider.verify(
                request.current_password, account.password_hash
            ):
                raise InvalidCredentialsError
            now = self._clock_provider.now()
            account.replace_password(
                self._password_hashing_provider.hash(request.new_password),
                now,
                retained_session_id=user.session_id,
                retained_session_access_version=user.token_access_version,
            )
            repositories.accounts.update(account)
            for token in repositories.account_action_tokens.find_many_pending_by_account_id_and_type(
                account.id,
                AccountActionTokenType.PASSWORD_RECOVERY,
            ):
                token.invalidate(now)
                repositories.account_action_tokens.update(token)
                if token.communication_id is not None:
                    repositories.events.add(
                        AccountActionTokenCancelledEvent(
                            payload=AccountActionTokenCancelledPayload(
                                communication_id=token.communication_id,
                                identity_action_token_id=token.id,
                                reason=AccountActionTokenCancellationReason.RESET,
                            )
                        )
                    )
