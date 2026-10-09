from shifu.shared.core.domain.errors import ConflictError


class MentorResponseConflictError(ConflictError):
    message: str = 'Esta mensagem já possui uma resposta diferente.'
