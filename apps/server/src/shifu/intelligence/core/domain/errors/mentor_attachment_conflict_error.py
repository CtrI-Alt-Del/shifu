from shifu.shared.core.domain.errors import ConflictError


class MentorAttachmentConflictError(ConflictError):
    message: str = 'O anexo não pode ser alterado neste estado.'
