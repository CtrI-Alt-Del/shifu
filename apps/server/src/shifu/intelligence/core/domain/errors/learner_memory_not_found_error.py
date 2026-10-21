from shifu.shared.core.domain.errors import NotFoundError


class LearnerMemoryNotFoundError(NotFoundError):
    message: str = 'Memória não encontrada.'
