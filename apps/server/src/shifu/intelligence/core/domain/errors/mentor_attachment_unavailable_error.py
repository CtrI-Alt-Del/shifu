from shifu.shared.core.domain.errors import ServiceUnavailableError


class MentorAttachmentUnavailableError(ServiceUnavailableError):
    message: str = 'Não foi possível acessar o arquivo.'
