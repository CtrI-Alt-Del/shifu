from shifu.shared.core.domain.errors import ServiceUnavailableError


class EvaluationUnavailableError(ServiceUnavailableError):
    message: str = 'Não foi possível concluir a avaliação.'
