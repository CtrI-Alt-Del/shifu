from shifu.shared.core.domain.errors import ConflictError


class AccountActionTokenInvalidatedError(ConflictError):
    message: str = 'O link informado não é mais válido.'
