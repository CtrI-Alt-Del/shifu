from datetime import timedelta
from math import ceil
from typing import ClassVar

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
from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.structures import PasswordRecoveryStatusResult
from shifu.identity.core.interfaces import (
    AccountActionTokensRepository,
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.shared.core.interfaces import ClockProvider


class GetPasswordRecoveryStatusUseCase:
    REQUEST_COOLDOWN: ClassVar[timedelta] = timedelta(seconds=60)

    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        recovery_handle_provider: ActionTokenProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider
        self._recovery_handle_provider = recovery_handle_provider

    def execute(self, recovery_handle: str) -> PasswordRecoveryStatusResult:
        handle_hash = self._recovery_handle_provider.hash(recovery_handle)
        now = self._clock_provider.now()
        with self._identity_database.transaction() as repositories:
            token_repository = self._token_repository(repositories)
            token = token_repository.find_by_pending_handle_hash(handle_hash)
            if (
                token is None
                or token.type is not AccountActionTokenType.PASSWORD_RECOVERY
            ):
                return PasswordRecoveryStatusResult(state='delivery_issue')
            account = repositories.accounts.find_by_id(token.account_id)
            if account is None or account.status not in {
                AccountStatus.ACTIVE,
                AccountStatus.PENDING_CONFIRMATION,
            }:
                return PasswordRecoveryStatusResult(state='delivery_issue')
            if token.status is not AccountActionTokenStatus.PENDING:
                return PasswordRecoveryStatusResult(state='delivery_issue')
            if now >= token.expires_at:
                token.expire(now)
                token_repository.update(token)
                self._add_expiry_cancellation_event(repositories, token)
                return PasswordRecoveryStatusResult(state='delivery_issue')
            if token.delivery_status in {
                AccountActionTokenDeliveryStatus.DELIVERY_UNAVAILABLE,
                AccountActionTokenDeliveryStatus.TEMPORARY_FAILURE,
                AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
                AccountActionTokenDeliveryStatus.EXHAUSTED,
                AccountActionTokenDeliveryStatus.EXPIRED,
            }:
                return PasswordRecoveryStatusResult(state='delivery_issue')
            cooldown_ends_at = token.issued_at + self.REQUEST_COOLDOWN
            if now < cooldown_ends_at:
                return PasswordRecoveryStatusResult(
                    state='cooldown',
                    retry_after_seconds=max(
                        1,
                        ceil((cooldown_ends_at - now).total_seconds()),
                    ),
                )
            return PasswordRecoveryStatusResult(state='ready')

    @staticmethod
    def _token_repository(
        repositories: IdentityDatabaseRepositories,
    ) -> AccountActionTokensRepository:
        return repositories.account_action_tokens

    @staticmethod
    def _add_expiry_cancellation_event(
        repositories: IdentityDatabaseRepositories,
        token: AccountActionToken,
    ) -> None:
        if token.communication_id is None:
            return
        repositories.events.add(
            AccountActionTokenCancelledEvent(
                payload=AccountActionTokenCancelledPayload(
                    communication_id=token.communication_id,
                    identity_action_token_id=token.id,
                    reason=AccountActionTokenCancellationReason.EXPIRED,
                )
            )
        )
