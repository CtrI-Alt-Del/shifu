from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenCancellationReason,
    AccountActionTokenDeliveryStatus,
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
)
from shifu.identity.core.domain.events import (
    AccountActionTokenCancelledEvent,
    AccountActionTokenCancelledPayload,
)
from shifu.identity.core.domain.structures import (
    PasswordRecoveryRequestResult,
)
from shifu.identity.core.interfaces import (
    AccountActionTokensRepository,
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
    PasswordRecoveryDeliveryGateway,
)
from shifu.identity.core.use_cases.request_password_recovery_use_case import (
    RequestPasswordRecoveryUseCase,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class RetryPasswordRecoveryUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        action_token_provider: ActionTokenProvider,
        recovery_handle_provider: ActionTokenProvider,
        delivery_gateway: PasswordRecoveryDeliveryGateway | None = None,
    ) -> None:
        self._identity_database = identity_database
        self._id_provider = id_provider
        self._clock_provider = clock_provider
        self._action_token_provider = action_token_provider
        self._recovery_handle_provider = recovery_handle_provider
        self._delivery_gateway = delivery_gateway

    def execute(self, recovery_handle: str) -> PasswordRecoveryRequestResult:
        now = self._clock_provider.now()
        handle_hash = self._recovery_handle_provider.hash(recovery_handle)
        with self._identity_database.transaction() as repositories:
            token_repository = self._token_repository(repositories)
            token = token_repository.find_by_pending_handle_hash(handle_hash)
            if (
                token is None
                or token.type is not AccountActionTokenType.PASSWORD_RECOVERY
            ):
                return PasswordRecoveryRequestResult(
                    recovery_handle=recovery_handle,
                    is_decoy=True,
                )
            account = repositories.accounts.find_by_id(token.account_id)
            if account is None or account.status not in {
                AccountStatus.ACTIVE,
                AccountStatus.PENDING_CONFIRMATION,
            }:
                return PasswordRecoveryRequestResult(
                    recovery_handle=recovery_handle,
                    is_decoy=True,
                )
            if token.status is not AccountActionTokenStatus.PENDING:
                return PasswordRecoveryRequestResult(
                    recovery_handle=recovery_handle,
                    is_decoy=True,
                )
            if now >= token.expires_at:
                token.expire(now)
                token_repository.update(token)
                self._add_cancellation_event(
                    repositories,
                    token,
                    AccountActionTokenCancellationReason.EXPIRED,
                )
                return PasswordRecoveryRequestResult(
                    recovery_handle=recovery_handle,
                    is_decoy=True,
                )
            if token.delivery_status not in {
                AccountActionTokenDeliveryStatus.DELIVERY_UNAVAILABLE,
                AccountActionTokenDeliveryStatus.TEMPORARY_FAILURE,
                AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
                AccountActionTokenDeliveryStatus.EXHAUSTED,
            }:
                return PasswordRecoveryRequestResult(
                    recovery_handle=recovery_handle,
                    is_decoy=False,
                )

            issuer = RequestPasswordRecoveryUseCase(
                identity_database=self._identity_database,
                id_provider=self._id_provider,
                clock_provider=self._clock_provider,
                action_token_provider=self._action_token_provider,
                recovery_handle_provider=self._recovery_handle_provider,
                delivery_gateway=self._delivery_gateway,
            )
            snapshot = issuer.issue_token(
                repositories=repositories,
                account_id=account.id,
                recipient_email=account.email,
                handle=recovery_handle,
                issued_at=now,
                cancellation_reason=AccountActionTokenCancellationReason.REISSUED,
            )

        issuer.queue_and_record(snapshot)
        return PasswordRecoveryRequestResult(
            recovery_handle=recovery_handle,
            is_decoy=False,
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
