from shifu.shared.core.domain.errors import ValidationError


class MentorTitleOutputInvalidError(ValidationError):
    message: str = 'O título gerado não é válido.'
