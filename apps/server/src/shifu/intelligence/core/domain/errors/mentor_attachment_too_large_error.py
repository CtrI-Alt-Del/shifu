from shifu.shared.core.domain.errors import ValidationError


class MentorAttachmentTooLargeError(ValidationError):
    message: str = 'O arquivo excede o limite de 2 MB.'
