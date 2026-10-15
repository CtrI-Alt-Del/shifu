from shifu.shared.core.domain.errors import NotFoundError


class MentorAttachmentNotFoundError(NotFoundError):
    message: str = 'Anexo do Mentor não encontrado.'
