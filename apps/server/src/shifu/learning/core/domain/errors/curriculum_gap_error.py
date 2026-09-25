from shifu.shared.core.domain.errors import ConflictError


class CurriculumGapError(ConflictError):
    message = 'Este Skill ainda não está pronto para iniciar.'
