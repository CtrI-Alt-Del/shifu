from shifu.shared.core.domain.errors.app_error import AppError


class AuthorizationError(AppError):
    title: str = 'Acesso não autorizado'
