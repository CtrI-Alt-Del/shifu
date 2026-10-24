from datetime import timedelta
from math import ceil
from typing import ClassVar

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountActionTokenCancellationReason,
    AccountStatus,
    ResendConfirmationResultStatus,
)
from shifu.identity.core.domain.events import (
    AccountActionTokenCancelledEvent,
    AccountActionTokenCancelledPayload,
)
from shifu.identity.core.domain.structures import ResendConfirmationResult
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationDeliveryRequest,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases.queue_confirmation_delivery_use_case import (
    QueueConfirmationDeliveryUseCase,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class ResendEmailConfirmationUseCase:
    RESEND_COOLDOWN: ClassVar[timedelta] = timedelta(seconds=60)
    CONFIRMATION_TOKEN_LIFETIME: ClassVar[timedelta] = timedelta(hours=24)

    def __init__(
        self,
        identity_database: IdentityDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        action_token_provider: ActionTokenProvider,
        pending_confirmation_handle_provider: ActionTokenProvider | None = None,
        queue_confirmation_delivery_use_case: (
            QueueConfirmationDeliveryUseCase | None
        ) = None,
    ) -> None:
        self._identity_database = identity_database
        self._id_provider = id_provider
        self._clock_provider = clock_provider
        self._action_token_provider = action_token_provider
        self._pending_confirmation_handle_provider = (
            pending_confirmation_handle_provider or action_token_provider
        )
        self._queue_confirmation_delivery_use_case = (
            queue_confirmation_delivery_use_case
        )

    def execute(self, pending_handle: str) -> ResendConfirmationResult:
        result = self._resend(pending_handle)
        if self._queue_confirmation_delivery_use_case is None:
            return result

        delivery_request = self._load_delivery_request(result)
        if delivery_request is not None:
            self._queue_confirmation_delivery_use_case.execute(delivery_request)

        return result

    def _resend(self, pending_handle: str) -> ResendConfirmationResult:
        pending_handle_hash = self._pending_confirmation_handle_provider.hash(
            pending_handle
        )
        now = self._clock_provider.now()

        with self._identity_database.transaction() as repositories:
            token_repository = repositories.account_action_tokens
            handle_token = token_repository.find_by_pending_handle_hash(
                pending_handle_hash
            )
            if handle_token is None:
                return self._accepted_result()

            account = repositories.accounts.find_by_id(handle_token.account_id)
            if (
                account is None
                or account.status is not AccountStatus.PENDING_CONFIRMATION
            ):
                return self._accepted_result()

            latest_token = (
                token_repository.find_latest_by_account_id_and_type(
                    account.id,
                    AccountActionTokenType.EMAIL_CONFIRMATION,
                )
            ) or handle_token
            cooldown_ends_at = latest_token.issued_at + self.RESEND_COOLDOWN
            if now < cooldown_ends_at:
                return ResendConfirmationResult(
                    result=ResendConfirmationResultStatus.COOLDOWN,
                    retry_after_seconds=max(
                        1,
                        ceil((cooldown_ends_at - now).total_seconds()),
                    ),
                )

            pending_tokens = token_repository.find_many_pending_by_account_id_and_type(
                account.id,
                AccountActionTokenType.EMAIL_CONFIRMATION,
            )
            for old_token in pending_tokens:
                old_token.invalidate(now)
                token_repository.update(old_token)
                self._add_cancellation_event(repositories, old_token)

            identity_action_token_id = self._id_provider.generate()
            communication_id = self._id_provider.generate()
            confirmation_token = self._action_token_provider.generate()
            expires_at = now + self.CONFIRMATION_TOKEN_LIFETIME
            replacement_token = AccountActionToken(
                id=identity_action_token_id,
                account_id=account.id,
                type=AccountActionTokenType.EMAIL_CONFIRMATION,
                status=AccountActionTokenStatus.PENDING,
                token_hash=self._action_token_provider.hash(confirmation_token),
                issued_at=now,
                expires_at=expires_at,
                updated_at=now,
                communication_id=communication_id,
                pending_handle_hash=pending_handle_hash,
            )
            token_repository.add(replacement_token)
            return ResendConfirmationResult(
                result=ResendConfirmationResultStatus.ACCEPTED,
                identity_action_token_id=identity_action_token_id,
                communication_id=communication_id,
                confirmation_token=confirmation_token,
                confirmation_expires_at=expires_at,
            )

    def _load_delivery_request(
        self,
        result: ResendConfirmationResult,
    ) -> ConfirmationDeliveryRequest | None:
        if (
            result.identity_action_token_id is None
            or result.communication_id is None
            or result.confirmation_token is None
            or result.confirmation_expires_at is None
        ):
            return None

        with self._identity_database.transaction() as repositories:
            token = repositories.account_action_tokens.find_by_id(
                result.identity_action_token_id
            )
            if token is None or token.pending_handle_hash is None:
                return None

            account = repositories.accounts.find_by_id(token.account_id)
            if (
                account is None
                or account.status is not AccountStatus.PENDING_CONFIRMATION
            ):
                return None

            return ConfirmationDeliveryRequest(
                communication_id=result.communication_id,
                identity_action_token_id=result.identity_action_token_id,
                account_id=account.id,
                recipient_email=account.email,
                recipient_name=account.display_name,
                confirmation_token=result.confirmation_token,
                expires_at=result.confirmation_expires_at,
            )

    @staticmethod
    def _accepted_result() -> ResendConfirmationResult:
        return ResendConfirmationResult(result=ResendConfirmationResultStatus.ACCEPTED)

    @staticmethod
    def _add_cancellation_event(
        repositories: IdentityDatabaseRepositories,
        confirmation_token: AccountActionToken,
    ) -> None:
        if confirmation_token.communication_id is None:
            return

        repositories.events.add(
            AccountActionTokenCancelledEvent(
                payload=AccountActionTokenCancelledPayload(
                    communication_id=confirmation_token.communication_id,
                    identity_action_token_id=confirmation_token.id,
                    reason=AccountActionTokenCancellationReason.REISSUED,
                )
            )
        )
