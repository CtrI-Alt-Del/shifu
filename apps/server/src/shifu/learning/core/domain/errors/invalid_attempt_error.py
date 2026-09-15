from shifu.shared.core.domain.errors import ValidationError


class InvalidAttemptError(ValidationError):
    message: str = 'A tentativa enviada é inválida.'
