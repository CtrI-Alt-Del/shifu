from shifu.shared.core.domain.errors import NotFoundError


class MaterialDetailNotFoundError(NotFoundError):
    message: str = 'Recurso não encontrado.'
