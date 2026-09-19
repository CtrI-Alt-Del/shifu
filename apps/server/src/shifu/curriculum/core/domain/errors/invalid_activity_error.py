from shifu.shared.core.domain.errors import ValidationError


class InvalidActivityError(ValidationError):
    message: str = 'A atividade curricular é inválida.'
