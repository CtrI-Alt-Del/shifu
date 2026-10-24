from datetime import timedelta
from math import ceil
from typing import ClassVar

from shifu.identity.core.domain.enums import (
    AccountActionTokenDeliveryStatus,
    AccountActionTokenStatus,
    AccountStatus,
)
from shifu.identity.core.domain.structures import PendingConfirmationStatusResult
from shifu.identity.core.interfaces import ActionTokenProvider, IdentityDatabase
from shifu.shared.core.interfaces import ClockProvider


class GetPendingConfirmationStatusUseCase:
    RESEND_COOLDOWN: ClassVar[timedelta] = timedelta(seconds=60)
    DELIVERY_ISSUE_STATUSES: ClassVar[frozenset[AccountActionTokenDeliveryStatus]] = (
        frozenset(
            {
                AccountActionTokenDeliveryStatus.DELIVERY_UNAVAILABLE,
                AccountActionTokenDeliveryStatus.TEMPORARY_FAILURE,
                AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
                AccountActionTokenDeliveryStatus.EXHAUSTED,
            }
        )
    )

    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        pending_confirmation_handle_provider: ActionTokenProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider
        self._pending_confirmation_handle_provider = (
            pending_confirmation_handle_provider
        )

    def execute(self, pending_handle: str) -> PendingConfirmationStatusResult:
        pending_handle_hash = self._pending_confirmation_handle_provider.hash(
            pending_handle
        )
        now = self._clock_provider.now()

        with self._identity_database.transaction() as repositories:
            token_repository = repositories.account_action_tokens
            token = token_repository.find_by_pending_handle_hash(pending_handle_hash)
            if token is None:
                return PendingConfirmationStatusResult(state='delivery_issue')

            account = repositories.accounts.find_by_id(token.account_id)
            if (
                account is None
                or account.status is not AccountStatus.PENDING_CONFIRMATION
            ):
                return PendingConfirmationStatusResult(state='delivery_issue')

            latest_token = (
                token_repository.find_latest_by_account_id_and_type(
                    account.id,
                    token.type,
                )
                or token
            )
            if latest_token.status is not AccountActionTokenStatus.PENDING:
                return PendingConfirmationStatusResult(state='delivery_issue')

            if latest_token.delivery_status in self.DELIVERY_ISSUE_STATUSES:
                return PendingConfirmationStatusResult(state='delivery_issue')

            cooldown_ends_at = latest_token.issued_at + self.RESEND_COOLDOWN
            if now < cooldown_ends_at:
                return PendingConfirmationStatusResult(
                    state='cooldown',
                    retry_after_seconds=max(
                        1,
                        ceil((cooldown_ends_at - now).total_seconds()),
                    ),
                )

            return PendingConfirmationStatusResult(state='ready')
