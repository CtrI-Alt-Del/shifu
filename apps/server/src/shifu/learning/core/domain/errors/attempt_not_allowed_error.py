from shifu.shared.core.domain.errors import ConflictError


class AttemptNotAllowedError(ConflictError):
    message: str = 'Uma nova tentativa não está disponível neste momento.'
