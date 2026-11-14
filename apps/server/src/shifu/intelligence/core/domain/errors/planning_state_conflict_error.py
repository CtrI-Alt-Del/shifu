from shifu.shared.core.domain.errors import ConflictError


class PlanningStateConflictError(ConflictError):
    message: str = 'O planejamento não aceita esta ação no estado atual.'
