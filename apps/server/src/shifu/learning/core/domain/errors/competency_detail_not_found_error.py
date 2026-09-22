from shifu.shared.core.domain.errors import NotFoundError


class CompetencyDetailNotFoundError(NotFoundError):
    message: str = 'Recurso não encontrado.'
