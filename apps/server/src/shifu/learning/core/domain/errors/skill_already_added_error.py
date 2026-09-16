from shifu.shared.core.domain.errors import ConflictError


class SkillAlreadyAddedError(ConflictError):
    message: str = 'A habilidade já pertence a este objetivo.'
