from shifu.shared.core.domain.errors import ValidationError


class InvalidCompetencyError(ValidationError):
    message: str = 'A competência curricular é inválida.'
