from shifu.shared.core.domain.structures import structure


@structure
class AuthCredentials:
    email: str
    password: str
