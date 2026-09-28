from datetime import datetime
from typing import Literal

from shifu.identity.core.domain.errors import InvalidEmailError, InvalidPasswordError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import normalize_email, require_non_empty


@structure
class PasswordRecoveryRequest:
    email: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'email', normalize_email(self.email, InvalidEmailError)
        )


@structure
class PasswordRecoveryRequestResult:
    recovery_handle: str
    is_decoy: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'recovery_handle',
            require_non_empty(self.recovery_handle, InvalidEmailError),
        )


@structure
class PasswordRecoveryStatusResult:
    state: Literal['ready', 'cooldown', 'delivery_issue']
    retry_after_seconds: int | None = None


@structure
class PasswordResetRequest:
    password: str
    password_confirmation: str

    def __post_init__(self) -> None:
        if len(self.password) < 8 or self.password != self.password_confirmation:
            raise InvalidPasswordError


@structure
class PasswordResetResult:
    result: Literal['reset', 'expired', 'used', 'invalid']
    account_id: str | None = None
    requires_email_confirmation: bool = False
    access_version: int | None = None


@structure
class PasswordResetLinkStatusResult:
    result: Literal['valid', 'expired', 'used', 'invalid']


@structure
class PasswordRecoveryDeliverySnapshot:
    identity_action_token_id: str
    communication_id: str
    account_id: str
    recipient_email: str
    recovery_token: str
    expires_at: datetime
