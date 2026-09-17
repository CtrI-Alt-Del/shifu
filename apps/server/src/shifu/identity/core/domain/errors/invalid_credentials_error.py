from shifu.shared.core.domain.errors import AuthorizationError


class InvalidCredentialsError(AuthorizationError):
    message: str = 'O e-mail ou a senha são inválidos.'
