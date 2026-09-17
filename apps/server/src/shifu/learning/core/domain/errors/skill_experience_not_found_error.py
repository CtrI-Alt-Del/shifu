from shifu.shared.core.domain.errors import NotFoundError


class SkillExperienceNotFoundError(NotFoundError):
    message: str = 'A experiência da habilidade não foi encontrada.'
