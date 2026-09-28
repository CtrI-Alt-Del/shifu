from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenCancellationReason,
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
)
from shifu.identity.core.domain.events import (
    AccountActionTokenCancelledEvent,
    AccountActionTokenCancelledPayload,
    AccountPasswordRecoveredEvent,
    AccountPasswordRecoveredPayload,
)
from shifu.identity.core.domain.structures import (
    PasswordResetRequest,
    PasswordResetResult,
)
from shifu.identity.core.interfaces import (
    AccountActionTokensRepository,
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
    PasswordHashingProvider,
)
from shifu.shared.core.interfaces import ClockProvider


class ResetPasswordUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        action_token_provider: ActionTokenProvider,
        password_hashing_provider: PasswordHashingProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider
        self._action_token_provider = action_token_provider
        self._password_hashing_provider = password_hashing_provider

    def execute(
        self,
        token: str,
        password: str | PasswordResetRequest,
        password_confirmation: str | None = None,
    ) -> PasswordResetResult:
        reset_request = (
            password
            if isinstance(password, PasswordResetRequest)
            else PasswordResetRequest(
                password=password,
                password_confirmation=password_confirmation or '',
            )
        )
        now = self._clock_provider.now()
        token_hash = self._action_token_provider.hash(token)
        with self._identity_database.transaction() as repositories:
            token_repository = self._token_repository(repositories)
            action_token = token_repository.find_by_hash(token_hash)
            if action_token is None:
                return PasswordResetResult(result='invalid')
            if action_token.type is not AccountActionTokenType.PASSWORD_RECOVERY:
                return PasswordResetResult(result='invalid')
            if action_token.status is AccountActionTokenStatus.USED:
                return PasswordResetResult(result='used')
            if action_token.status is AccountActionTokenStatus.EXPIRED:
                return PasswordResetResult(result='expired')
            if action_token.status is AccountActionTokenStatus.INVALIDATED:
                return PasswordResetResult(result='invalid')
            if now >= action_token.expires_at:
                action_token.expire(now)
                token_repository.update(action_token)
                self._add_cancellation_event(
                    repositories,
                    action_token,
                    AccountActionTokenCancellationReason.EXPIRED,
                )
                return PasswordResetResult(result='expired')

            account = repositories.accounts.find_by_id(action_token.account_id)
            if account is None or account.status not in {
                AccountStatus.ACTIVE,
                AccountStatus.PENDING_CONFIRMATION,
            }:
                return PasswordResetResult(result='invalid')

            account.replace_password(
                self._password_hashing_provider.hash(reset_request.password),
                now,
            )
            action_token.use(now)
            repositories.accounts.update(account)
            token_repository.update(action_token)
            for sibling in token_repository.find_many_pending_by_account_id_and_type(
                account.id,
                AccountActionTokenType.PASSWORD_RECOVERY,
            ):
                if sibling.id == action_token.id:
                    continue
                sibling.invalidate(now)
                token_repository.update(sibling)
                self._add_cancellation_event(
                    repositories,
                    sibling,
                    AccountActionTokenCancellationReason.RESET,
                )
            self._add_cancellation_event(
                repositories,
                action_token,
                AccountActionTokenCancellationReason.RESET,
            )
            repositories.events.add(
                AccountPasswordRecoveredEvent(
                    payload=AccountPasswordRecoveredPayload(
                        account_id=account.id,
                        access_version=account.access_version,
                        recovered_at=now.isoformat(),
                    )
                )
            )
            return PasswordResetResult(
                result='reset',
                account_id=account.id,
                requires_email_confirmation=(
                    account.status is AccountStatus.PENDING_CONFIRMATION
                ),
                access_version=account.access_version,
            )

    @staticmethod
    def _token_repository(
        repositories: IdentityDatabaseRepositories,
    ) -> AccountActionTokensRepository:
        return repositories.account_action_tokens

    @staticmethod
    def _add_cancellation_event(
        repositories: IdentityDatabaseRepositories,
        token: AccountActionToken,
        reason: AccountActionTokenCancellationReason,
    ) -> None:
        if token.communication_id is None:
            return
        repositories.events.add(
            AccountActionTokenCancelledEvent(
                payload=AccountActionTokenCancelledPayload(
                    communication_id=token.communication_id,
                    identity_action_token_id=token.id,
                    reason=reason,
                )
            )
        )
