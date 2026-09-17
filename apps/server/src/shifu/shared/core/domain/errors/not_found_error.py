from shifu.shared.core.domain.errors.app_error import AppError


class NotFoundError(AppError):
    title: str = 'Recurso não encontrado'
