from datetime import datetime, timedelta
from typing import ClassVar

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenCancellationReason,
    AccountActionTokenDeliveryStatus,
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
    ActionTokenDeliveryQueueStatus,
)
from shifu.identity.core.domain.events import (
    AccountActionTokenCancelledEvent,
    AccountActionTokenCancelledPayload,
)
from shifu.identity.core.domain.structures import (
    PasswordRecoveryDeliverySnapshot,
    PasswordRecoveryRequest,
    PasswordRecoveryRequestResult,
)
from shifu.identity.core.interfaces import (
    AccountActionTokensRepository,
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
    PasswordRecoveryDeliveryGateway,
    PasswordRecoveryDeliveryRequest,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class RequestPasswordRecoveryUseCase:
    RECOVERY_TOKEN_LIFETIME: ClassVar[timedelta] = timedelta(hours=1)
    REQUEST_COOLDOWN: ClassVar[timedelta] = timedelta(seconds=60)

    def __init__(
        self,
        identity_database: IdentityDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        action_token_provider: ActionTokenProvider,
        recovery_handle_provider: ActionTokenProvider | None = None,
        delivery_gateway: PasswordRecoveryDeliveryGateway | None = None,
    ) -> None:
        self._identity_database = identity_database
        self._id_provider = id_provider
        self._clock_provider = clock_provider
        self._action_token_provider = action_token_provider
        self._recovery_handle_provider = (
            recovery_handle_provider or action_token_provider
        )
        self._delivery_gateway = delivery_gateway

    def execute(
        self,
        request: PasswordRecoveryRequest | str,
    ) -> PasswordRecoveryRequestResult:
        recovery_handle = self._recovery_handle_provider.generate()
        normalized_request = (
            request
            if isinstance(request, PasswordRecoveryRequest)
            else PasswordRecoveryRequest(email=request)
        )
        now = self._clock_provider.now()

        with self._identity_database.transaction() as repositories:
            account = repositories.accounts.find_non_deleted_by_email(
                normalized_request.email
            )
            if account is None or account.status not in {
                AccountStatus.ACTIVE,
                AccountStatus.PENDING_CONFIRMATION,
            }:
                return PasswordRecoveryRequestResult(
                    recovery_handle=recovery_handle,
                    is_decoy=True,
                )

            token_repository = self._token_repository(repositories)
            latest_token = token_repository.find_latest_by_account_id_and_type(
                account.id,
                AccountActionTokenType.PASSWORD_RECOVERY,
            )
            if latest_token is not None and now < (
                latest_token.issued_at + self.REQUEST_COOLDOWN
            ):
                return PasswordRecoveryRequestResult(
                    recovery_handle=recovery_handle,
                    is_decoy=True,
                )

            snapshot = self.issue_token(
                repositories=repositories,
                account_id=account.id,
                recipient_email=account.email,
                handle=recovery_handle,
                issued_at=now,
                cancellation_reason=AccountActionTokenCancellationReason.REISSUED,
            )

        self.queue_and_record(snapshot)
        return PasswordRecoveryRequestResult(
            recovery_handle=recovery_handle,
            is_decoy=False,
        )

    def queue_and_record(self, snapshot: PasswordRecoveryDeliverySnapshot) -> None:
        if self._delivery_gateway is None:
            return

        status = ActionTokenDeliveryQueueStatus.DELIVERY_UNAVAILABLE
        try:
            result = self._delivery_gateway.queue(
                PasswordRecoveryDeliveryRequest(
                    communication_id=snapshot.communication_id,
                    identity_action_token_id=snapshot.identity_action_token_id,
                    account_id=snapshot.account_id,
                    recipient_email=snapshot.recipient_email,
                    recovery_token=snapshot.recovery_token,
                    expires_at=snapshot.expires_at,
                )
            )
            status = result.status
        except Exception:  # noqa: BLE001 - queue failure is a safe delivery state.
            status = ActionTokenDeliveryQueueStatus.DELIVERY_UNAVAILABLE

        self._record_queue_status(snapshot.identity_action_token_id, status)

    def _record_queue_status(
        self,
        identity_action_token_id: str,
        status: ActionTokenDeliveryQueueStatus,
    ) -> None:
        with self._identity_database.transaction() as repositories:
            token_repository = self._token_repository(repositories)
            token = token_repository.find_by_id(identity_action_token_id)
            if token is None:
                return

            if token.record_delivery_status(
                AccountActionTokenDeliveryStatus(status.value),
                self._clock_provider.now(),
            ):
                token_repository.update(token)

    def issue_token(
        self,
        *,
        repositories: IdentityDatabaseRepositories,
        account_id: str,
        recipient_email: str,
        handle: str,
        issued_at: datetime,
        cancellation_reason: AccountActionTokenCancellationReason,
    ) -> PasswordRecoveryDeliverySnapshot:
        token_repository = self._token_repository(repositories)
        for old_token in token_repository.find_many_pending_by_account_id_and_type(
            account_id,
            AccountActionTokenType.PASSWORD_RECOVERY,
        ):
            old_token.invalidate(issued_at)
            token_repository.update(old_token)
            self._add_cancellation_event(repositories, old_token, cancellation_reason)

        identity_action_token_id = self._id_provider.generate()
        communication_id = self._id_provider.generate()
        recovery_token = self._action_token_provider.generate()
        expires_at = issued_at + self.RECOVERY_TOKEN_LIFETIME
        token = AccountActionToken(
            id=identity_action_token_id,
            account_id=account_id,
            type=AccountActionTokenType.PASSWORD_RECOVERY,
            status=AccountActionTokenStatus.PENDING,
            token_hash=self._action_token_provider.hash(recovery_token),
            issued_at=issued_at,
            expires_at=expires_at,
            updated_at=issued_at,
            communication_id=communication_id,
            pending_handle_hash=self._recovery_handle_provider.hash(handle),
        )
        token_repository.add(token)
        return PasswordRecoveryDeliverySnapshot(
            identity_action_token_id=identity_action_token_id,
            communication_id=communication_id,
            account_id=account_id,
            recipient_email=recipient_email,
            recovery_token=recovery_token,
            expires_at=expires_at,
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
