from shifu.shared.core.domain.errors import ValidationError


class MentorInputInvalidError(ValidationError):
    message: str = 'Os dados da conversa são inválidos.'
