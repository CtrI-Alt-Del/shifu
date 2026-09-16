from shifu.shared.core.domain.errors import ValidationError


class InvalidSkillError(ValidationError):
    message: str = 'A habilidade curricular é inválida.'
