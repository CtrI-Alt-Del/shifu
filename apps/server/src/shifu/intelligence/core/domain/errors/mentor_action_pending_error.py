from shifu.shared.core.domain.errors import ConflictError


class MentorActionPendingError(ConflictError):
    message: str = 'Confirme ou recuse a ação proposta para continuar.'
    title: str = 'Ação pendente'
