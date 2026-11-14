from shifu.identity.core.domain.errors import InvalidPasswordError
from shifu.shared.core.domain.structures import structure


@structure
class PasswordChangeRequest:
    current_password: str
    new_password: str

    def __post_init__(self) -> None:
        if len(self.new_password) < 8:
            raise InvalidPasswordError
