from shifu.shared.core.domain.errors import ConflictError


class AccountConfirmationNotAllowedError(ConflictError):
    message: str = 'A conta não pode ser confirmada no estado atual.'
