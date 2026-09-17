from shifu.shared.core.domain.errors.app_error import AppError


class ConflictError(AppError):
    title: str = 'Conflito de estado'
