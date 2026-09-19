from shifu.shared.core.domain.errors import ValidationError


class InvalidMaterialError(ValidationError):
    message: str = 'O material é inválido.'
