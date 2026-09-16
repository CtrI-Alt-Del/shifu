from shifu.shared.core.domain.errors import ConflictError


class EvaluationAlreadyCompletedError(ConflictError):
    message: str = 'A avaliação já foi concluída.'
