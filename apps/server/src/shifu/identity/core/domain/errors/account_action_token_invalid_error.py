from shifu.shared.core.domain.errors import NotFoundError


class AccountActionTokenInvalidError(NotFoundError):
    message: str = 'O link informado é inválido.'
