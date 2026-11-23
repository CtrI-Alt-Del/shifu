from shifu.shared.core.domain.errors import ValidationError


class PracticePhotoInvalidError(ValidationError):
    message: str = 'A foto não é válida. Use uma imagem JPEG, PNG ou WebP.'
