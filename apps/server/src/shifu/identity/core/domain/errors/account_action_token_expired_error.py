from shifu.shared.core.domain.errors import ConflictError


class AccountActionTokenExpiredError(ConflictError):
    message: str = 'O link informado expirou.'
