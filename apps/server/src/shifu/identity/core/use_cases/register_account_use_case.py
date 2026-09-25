from datetime import timedelta
from typing import ClassVar

from shifu.identity.core.domain.entities import Account, AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
)
from shifu.identity.core.domain.events import AccountCreatedEvent, AccountCreatedPayload
from shifu.identity.core.domain.structures import (
    AccountRegistration,
    AccountRegistrationResult,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    PasswordHashingProvider,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class RegisterAccountUseCase:
    CONFIRMATION_TOKEN_LIFETIME: ClassVar[timedelta] = timedelta(hours=24)

    def __init__(
        self,
        identity_database: IdentityDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        password_hashing_provider: PasswordHashingProvider,
        action_token_provider: ActionTokenProvider,
        pending_confirmation_handle_provider: ActionTokenProvider | None = None,
    ) -> None:
        self._identity_database = identity_database
        self._id_provider = id_provider
        self._clock_provider = clock_provider
        self._password_hashing_provider = password_hashing_provider
        self._action_token_provider = action_token_provider
        self._pending_confirmation_handle_provider = (
            pending_confirmation_handle_provider or action_token_provider
        )

    def execute(self, registration: AccountRegistration) -> AccountRegistrationResult:
        pending_handle = self._pending_confirmation_handle_provider.generate()
        pending_handle_hash = self._pending_confirmation_handle_provider.hash(
            pending_handle
        )

        with self._identity_database.transaction() as repositories:
            existing_account = repositories.accounts.find_non_deleted_by_email(
                registration.email
            )
            if existing_account is not None:
                return AccountRegistrationResult(
                    pending_handle=pending_handle,
                    account_id=None,
                    identity_confirmation_id=None,
                    communication_id=None,
                    confirmation_token=None,
                    confirmation_expires_at=None,
                )

            created_at = self._clock_provider.now()
            account_id = self._id_provider.generate()
            identity_confirmation_id = self._id_provider.generate()
            communication_id = self._id_provider.generate()
            confirmation_token = self._action_token_provider.generate()
            password_hash = self._password_hashing_provider.hash(registration.password)
            confirmation_expires_at = created_at + self.CONFIRMATION_TOKEN_LIFETIME

            account = Account.create(
                id=account_id,
                display_name=registration.display_name,
                email=registration.email,
                password_hash=password_hash,
                status=AccountStatus.PENDING_CONFIRMATION,
                access_version=1,
                time_zone=None,
                created_at=created_at,
                updated_at=created_at,
            )
            confirmation_token_entity = AccountActionToken(
                id=identity_confirmation_id,
                account_id=account_id,
                type=AccountActionTokenType.EMAIL_CONFIRMATION,
                status=AccountActionTokenStatus.PENDING,
                token_hash=self._action_token_provider.hash(confirmation_token),
                issued_at=created_at,
                expires_at=confirmation_expires_at,
                updated_at=created_at,
                communication_id=communication_id,
                pending_handle_hash=pending_handle_hash,
            )

            repositories.accounts.add(account)
            repositories.account_action_tokens.add(confirmation_token_entity)
            repositories.events.add(
                AccountCreatedEvent(
                    payload=AccountCreatedPayload(
                        account_id=account_id,
                        status=account.status,
                        created_at=created_at.isoformat(),
                    )
                )
            )

            return AccountRegistrationResult(
                pending_handle=pending_handle,
                account_id=account_id,
                identity_confirmation_id=identity_confirmation_id,
                communication_id=communication_id,
                confirmation_token=confirmation_token,
                confirmation_expires_at=confirmation_expires_at,
            )
