from shifu.shared.core.domain.errors import ConflictError


class SkillExperienceTransitionError(ConflictError):
    message: str = 'A habilidade não pode mudar para a etapa solicitada.'
