from shifu.shared.core.domain.errors import AuthorizationError


class ActivityNotAvailableError(AuthorizationError):
    message: str = 'A atividade ainda não está disponível nesta experiência.'
