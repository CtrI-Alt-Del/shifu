from shifu.shared.core.domain.errors import ConflictError


class LearnerMemoryConflictError(ConflictError):
    message: str = 'Esta memória foi alterada. Atualize para ver a versão mais recente.'
