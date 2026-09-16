from shifu.shared.core.domain.errors import ConflictError


class AccountDeletionNotAllowedError(ConflictError):
    message: str = 'A conta não pode ser excluída no estado atual.'
