from shifu.shared.core.domain.errors import AuthorizationError


class AccountNotActiveError(AuthorizationError):
    message: str = 'A conta não está ativa.'
