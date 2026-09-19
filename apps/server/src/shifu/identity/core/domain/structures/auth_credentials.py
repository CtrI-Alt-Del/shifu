from shifu.identity.core.domain.errors import InvalidPasswordError
from shifu.shared.core.domain.validation import normalize_email
from shifu.shared.core.domain.structures import structure


@structure
class AuthCredentials:
    email: str
    password: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'email', normalize_email(self.email))
        if len(self.password) < 8:
            raise InvalidPasswordError

    @classmethod
    def create(cls, *, email: str, password: str) -> 'AuthCredentials':
        return cls(email=email, password=password)
