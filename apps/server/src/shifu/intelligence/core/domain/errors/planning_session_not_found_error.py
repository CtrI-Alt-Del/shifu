from shifu.shared.core.domain.errors import NotFoundError


class PlanningSessionNotFoundError(NotFoundError):
    message: str = 'Planejamento não encontrado.'
