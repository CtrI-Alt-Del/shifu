from shifu.shared.core.domain.errors import ConflictError


class EvaluationPendingError(ConflictError):
    message: str = 'Uma avaliação desta habilidade ainda está em andamento.'
