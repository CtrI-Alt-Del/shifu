from shifu.identity.core.domain.errors import InvalidPasswordError
from shifu.shared.core.domain.structures import EmailAddress, structure


@structure
class AuthCredentials:
    email: str
    password: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'email', EmailAddress.create(self.email).value)

    @classmethod
    def create(cls, *, email: str, password: str) -> 'AuthCredentials':
        if len(password) < 8:
            raise InvalidPasswordError

        return cls(email=email, password=password)
