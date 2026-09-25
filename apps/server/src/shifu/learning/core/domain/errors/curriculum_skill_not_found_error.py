from shifu.shared.core.domain.errors import NotFoundError


class CurriculumSkillNotFoundError(NotFoundError):
    message: str = 'A habilidade não foi encontrada no currículo.'
