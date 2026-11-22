from shifu.shared.core.domain.errors import ConflictError


class PracticeDraftIncompleteError(ConflictError):
    message: str = 'Envie uma foto pronta para cada registro antes de enviar.'
    title: str = 'Rascunho incompleto'
