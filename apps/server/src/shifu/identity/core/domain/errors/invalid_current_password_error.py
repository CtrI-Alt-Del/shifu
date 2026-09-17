from shifu.shared.core.domain.errors import AuthorizationError


class InvalidCurrentPasswordError(AuthorizationError):
    message: str = 'A senha atual está incorreta.'
