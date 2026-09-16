from shifu.shared.core.domain.errors.app_error import AppError


class RateLimitError(AppError):
    title: str = 'Limite de solicitações atingido'
