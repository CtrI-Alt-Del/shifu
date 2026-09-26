from shifu.shared.core.domain.errors import NotFoundError


class SkillExperienceDetailNotFoundError(NotFoundError):
    message: str = 'Recurso não encontrado.'
