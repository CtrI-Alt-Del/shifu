from shifu.shared.core.domain.errors import ValidationError


class MentorCursorInvalidError(ValidationError):
    message: str = 'Cursor inválido.'
