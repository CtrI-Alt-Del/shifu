from datetime import datetime

from shifu.identity.core.domain.errors import (
    InvalidDisplayNameError,
    InvalidEmailError,
    InvalidPasswordError,
)
from shifu.shared.core.domain.structures import EmailAddress, NonEmptyText, structure


@structure
class AccountRegistration:
    display_name: str
    email: str
    password: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'display_name',
            NonEmptyText.create(
                self.display_name, error_type=InvalidDisplayNameError
            ).value,
        )
        object.__setattr__(
            self,
            'email',
            EmailAddress.create(self.email, error_type=InvalidEmailError).value,
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
    identity_action_token_id: str | None
    communication_id: str | None
    confirmation_token: str | None
    confirmation_expires_at: datetime | None
