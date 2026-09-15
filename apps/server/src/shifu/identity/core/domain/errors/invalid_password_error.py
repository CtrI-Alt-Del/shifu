from shifu.shared.core.domain.errors import ValidationError


class InvalidPasswordError(ValidationError):
    message: str = 'A senha deve possuir pelo menos 8 caracteres.'
