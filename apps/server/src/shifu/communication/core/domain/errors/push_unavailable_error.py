from shifu.shared.core.domain.errors import ServiceUnavailableError


class PushUnavailableError(ServiceUnavailableError):
    message: str = 'Os lembretes por notificação estão indisponíveis no momento.'
