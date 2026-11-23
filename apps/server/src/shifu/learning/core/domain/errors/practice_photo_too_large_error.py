from shifu.shared.core.domain.errors import ValidationError


class PracticePhotoTooLargeError(ValidationError):
    message: str = 'A foto excede o limite de 10 MB.'
