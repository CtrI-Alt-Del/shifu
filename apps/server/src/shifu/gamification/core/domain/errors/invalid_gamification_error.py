from shifu.shared.core.domain.errors import ValidationError


class InvalidGamificationError(ValidationError):
    title: str = 'Gamificação inválida'
    message: str = 'Os dados de gamificação são inválidos.'
