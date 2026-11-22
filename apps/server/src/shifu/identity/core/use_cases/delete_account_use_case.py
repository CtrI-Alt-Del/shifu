from datetime import timedelta
from hashlib import sha256

from shifu.identity.core.domain.entities import Account
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.domain.errors import (
    AccountDeletionNotAllowedError,
    InvalidCurrentPasswordError,
)
from shifu.identity.core.domain.events import (
    AccountErasureRequestedEvent,
    AccountErasureRequestedPayload,
)
from shifu.identity.core.domain.structures import (
    AccountErasureResult,
    DeleteAccountInput,
)
from shifu.identity.core.interfaces import IdentityDatabase, PasswordHashingProvider
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider


_ERASURE_PARTICIPANTS = (
    'identity-bff',
    'learning',
    'intelligence',
    'gamification',
    'communication',
)
_IDENTITY_ACCOUNT_EVENT_NAMES = {
    'identity/account.activated',
    'identity/account.created',
    'identity/account.deleted',
    'identity/account-deletion.requested',
    'identity/account.display-name-changed',
    'identity.account-expiry-requested',
    'identity/account.expired',
    'identity/account.password-changed',
    'identity/email-confirmation.requested',
    'identity/account.password-recovered',
    'app/main-page.entered',
    'identity/password-recovery.requested',
}
_COMMUNICATION_EVENT_NAMES = {
    'communication/communication.queued',
    'communication.delivery-state-changed',
}


class DeleteAccountUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        password_hashing_provider: PasswordHashingProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider
        self._password_hashing_provider = password_hashing_provider

    def execute(
        self, user: AuthenticatedUser, request: DeleteAccountInput
    ) -> AccountErasureResult:
        if not request.confirmed:
            raise AccountDeletionNotAllowedError
        if request.account_id != user.account_id:
            raise AuthorizationError

        with self._identity_database.account_closure_transaction(
            request.account_id
        ) as repositories:
            existing = repositories.account_erasures.find_result(request.erasure_id)
            if existing is not None:
                owner = repositories.account_erasures.find_account_id(
                    request.erasure_id
                )
                if owner is None or owner != user.account_id:
                    raise AuthorizationError
                return existing

            account = repositories.accounts.find_by_id(request.account_id)
            if account is None:
                raise AccountDeletionNotAllowedError
            self._validate_actor(account, user)
            if not self._password_hashing_provider.verify(
                request.current_password, account.password_hash
            ):
                raise InvalidCurrentPasswordError
            if repositories.external_effect_receipts.has_unresolved_for_account_id(
                account.id
            ):
                raise AccountDeletionNotAllowedError

            closed_at = self._clock_provider.now()
            account.delete(closed_at)
            account.anonymize(
                replacement_email=self._replacement_email(account.id),
                updated_at=closed_at,
            )
            repositories.accounts.update(account)
            repositories.external_effect_receipts.remove_settled_for_account_id(
                account.id
            )
            communication_ids = (
                repositories.account_action_tokens.find_communication_ids_by_account_id(
                    account.id
                )
            )
            for event_name in _COMMUNICATION_EVENT_NAMES:
                repositories.events.remove_by_payload_values(
                    event_name,
                    'communication_id',
                    communication_ids,
                )
            repositories.account_action_tokens.remove_by_account_id(account.id)
            repositories.account_browser_capabilities.revoke_by_account_id(account.id)
            repositories.events.remove_by_account_id_and_names(
                account.id,
                _IDENTITY_ACCOUNT_EVENT_NAMES,
            )
            repositories.account_erasures.add(
                erasure_id=request.erasure_id,
                account_id=account.id,
                closed_at=closed_at,
                due_at=closed_at + timedelta(hours=24),
                participants=_ERASURE_PARTICIPANTS,
            )
            repositories.events.add(
                AccountErasureRequestedEvent(
                    payload=AccountErasureRequestedPayload(
                        erasure_id=str(request.erasure_id)
                    )
                )
            )
            return AccountErasureResult(
                state='closed', closed_at=closed_at, erasure='pending'
            )

    @staticmethod
    def _validate_actor(account: Account, user: AuthenticatedUser) -> None:
        if account.status is not AccountStatus.ACTIVE:
            raise AccountDeletionNotAllowedError
        if (
            user.session_id is None
            or user.token_access_version is None
            or user.account_access_version != account.access_version
            or not account.accepts_access(user.session_id, user.token_access_version)
        ):
            raise AuthorizationError

    @staticmethod
    def _replacement_email(account_id: str) -> str:
        digest = sha256(account_id.encode('utf-8')).hexdigest()[:32]
        return f'closed-{digest}@invalid.local'
