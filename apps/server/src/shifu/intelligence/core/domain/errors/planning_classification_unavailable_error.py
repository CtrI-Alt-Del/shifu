from shifu.shared.core.domain.errors import ServiceUnavailableError


class PlanningClassificationUnavailableError(ServiceUnavailableError):
    message: str = 'A classificação da intenção do Planejador está indisponível.'
