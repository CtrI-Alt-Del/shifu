from shifu.shared.core.domain.errors.app_error import AppError


class ValidationError(AppError):
    title: str = 'Dados inválidos'
