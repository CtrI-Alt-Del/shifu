from shifu.shared.core.domain.errors import ValidationError


class InvalidDisplayNameError(ValidationError):
    message: str = 'O nome de exibição é obrigatório.'
