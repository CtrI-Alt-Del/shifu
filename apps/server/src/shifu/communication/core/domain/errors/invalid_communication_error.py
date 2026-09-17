from shifu.shared.core.domain.errors import ValidationError


class InvalidCommunicationError(ValidationError):
    message: str = 'A comunicação é inválida.'
