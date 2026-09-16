from shifu.shared.core.domain.errors.app_error import AppError


class ServiceUnavailableError(AppError):
    title: str = 'Serviço indisponível'
