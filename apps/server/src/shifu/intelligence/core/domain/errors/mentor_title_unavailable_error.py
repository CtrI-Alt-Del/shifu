from shifu.shared.core.domain.errors import ServiceUnavailableError


class MentorTitleUnavailableError(ServiceUnavailableError):
    message: str = 'A geração do título está indisponível.'
