from shifu.shared.core.domain.errors import ValidationError


class InvalidGoalError(ValidationError):
    message: str = 'O objetivo de aprendizagem é inválido.'
