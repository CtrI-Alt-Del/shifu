from shifu.shared.core.domain.errors import ConflictError


class CommunicationTransitionError(ConflictError):
    message: str = 'A comunicação não pode mudar para a etapa solicitada.'
