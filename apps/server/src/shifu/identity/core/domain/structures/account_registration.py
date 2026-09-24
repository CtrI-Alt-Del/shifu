from datetime import datetime

from shifu.identity.core.domain.errors import (
    InvalidDisplayNameError,
    InvalidEmailError,
    InvalidPasswordError,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import normalize_email, require_non_empty


@structure
class AccountRegistration:
    display_name: str
    email: str
    password: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'display_name',
            require_non_empty(self.display_name, InvalidDisplayNameError),
        )
        object.__setattr__(
            self,
            'email',
            normalize_email(self.email, InvalidEmailError),
        )
        if len(self.password) < 8:
            raise InvalidPasswordError

    @classmethod
    def create(
        cls,
        *,
        display_name: str,
        email: str,
        password: str,
    ) -> 'AccountRegistration':
        return cls(display_name=display_name, email=email, password=password)


@structure
class AccountRegistrationResult:
    """Internal result; raw handles and tokens never cross the browser boundary."""

    pending_handle: str
    account_id: str | None
    identity_confirmation_id: str | None
    communication_id: str | None
    confirmation_token: str | None
    confirmation_expires_at: datetime | None
