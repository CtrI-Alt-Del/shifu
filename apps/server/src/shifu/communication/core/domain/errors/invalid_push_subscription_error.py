from shifu.shared.core.domain.errors import ValidationError


class InvalidPushSubscriptionError(ValidationError):
    message: str = 'Não foi possível registrar este navegador para lembretes.'
