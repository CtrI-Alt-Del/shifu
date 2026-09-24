from datetime import datetime, timedelta
from typing import ClassVar, cast

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountConfirmationCancellationReason,
    AccountStatus,
)
from shifu.identity.core.domain.events import (
    AccountConfirmationCancelledEvent,
    AccountConfirmationCancelledPayload,
    AccountExpiredEvent,
    AccountExpiredPayload,
    AccountExpiryRequestedEvent,
    AccountExpiryRequestedPayload,
)
from shifu.identity.core.interfaces import (
    ConfirmationAccountActionTokensRepository,
    ExpiringAccountsRepository,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.shared.core.interfaces import ClockProvider


class ExpireUnconfirmedAccountsUseCase:
    ACCOUNT_LIFETIME: ClassVar[timedelta] = timedelta(days=7)
    MAX_BATCH_SIZE: ClassVar[int] = 100

    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider

    def execute(self, account_id: str | None = None) -> tuple[str, ...]:
        now = self._clock_provider.now()
        if account_id is None:
            return self._claim_expiry_batch(now)
        return self._expire_account(account_id, now)

    def _claim_expiry_batch(self, now: datetime) -> tuple[str, ...]:
        created_before = now - self.ACCOUNT_LIFETIME
        with self._identity_database.transaction() as repositories:
            accounts_repository = cast(
                'ExpiringAccountsRepository',
                repositories.accounts,
            )
            candidates = accounts_repository.find_many_pending_created_before(
                created_before,
                limit=self.MAX_BATCH_SIZE,
            )
            account_ids: list[str] = []
            for account in candidates[: self.MAX_BATCH_SIZE]:
                if account.status is not AccountStatus.PENDING_CONFIRMATION:
                    continue
                if account.created_at + self.ACCOUNT_LIFETIME > now:
                    continue
                account_ids.append(account.id)
                repositories.events.add(
                    AccountExpiryRequestedEvent(
                        payload=AccountExpiryRequestedPayload(account_id=account.id)
                    )
                )
            return tuple(account_ids)

    def _expire_account(self, account_id: str, now: datetime) -> tuple[str, ...]:
        with self._identity_database.transaction() as repositories:
            account = repositories.accounts.find_by_id(account_id)
            if account is None:
                return ()
            if account.status is not AccountStatus.PENDING_CONFIRMATION:
                return ()
            if account.created_at + self.ACCOUNT_LIFETIME > now:
                return ()

            account.expire(now)
            repositories.accounts.update(account)
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            confirmation_tokens = token_repository.find_many_by_account_id_and_type(
                account.id,
                AccountActionTokenType.EMAIL_CONFIRMATION,
            )
            for confirmation_token in confirmation_tokens:
                if confirmation_token.status is AccountActionTokenStatus.PENDING:
                    confirmation_token.expire(now)
                    token_repository.update(confirmation_token)
                self._add_cancellation_event(repositories, confirmation_token)

            repositories.events.add(
                AccountExpiredEvent(
                    payload=AccountExpiredPayload(
                        account_id=account.id,
                        expired_at=now.isoformat(),
                    )
                )
            )
            return (account.id,)

    @staticmethod
    def _add_cancellation_event(
        repositories: IdentityDatabaseRepositories,
        confirmation_token: AccountActionToken,
    ) -> None:
        if confirmation_token.communication_id is None:
            return
        repositories.events.add(
            AccountConfirmationCancelledEvent(
                payload=AccountConfirmationCancelledPayload(
                    communication_id=confirmation_token.communication_id,
                    identity_confirmation_id=confirmation_token.id,
                    reason=AccountConfirmationCancellationReason.EXPIRED,
                )
            )
        )
