from shifu.shared.core.domain.errors import ValidationError


class MentorAttachmentInvalidError(ValidationError):
    message: str = 'O arquivo não é válido ou não é compatível.'
