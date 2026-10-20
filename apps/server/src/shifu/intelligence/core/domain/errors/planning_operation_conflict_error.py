from shifu.shared.core.domain.errors import ConflictError


class PlanningOperationConflictError(ConflictError):
    message: str = 'Já existe uma operação em andamento neste planejamento.'
