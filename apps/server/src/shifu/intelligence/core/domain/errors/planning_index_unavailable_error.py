from shifu.shared.core.domain.errors import ServiceUnavailableError


class PlanningIndexUnavailableError(ServiceUnavailableError):
    message: str = 'O índice de Habilidades do Planejador está indisponível.'
