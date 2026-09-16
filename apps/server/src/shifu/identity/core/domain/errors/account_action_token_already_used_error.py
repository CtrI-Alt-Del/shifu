from shifu.shared.core.domain.errors import ConflictError


class AccountActionTokenAlreadyUsedError(ConflictError):
    message: str = 'O link informado já foi utilizado.'
