from shifu.shared.core.domain.errors import ConflictError


class PracticeDraftConflictError(ConflictError):
    message: str = 'O rascunho foi alterado ou encerrado. Recarregue para continuar.'
    title: str = 'Rascunho em conflito'
