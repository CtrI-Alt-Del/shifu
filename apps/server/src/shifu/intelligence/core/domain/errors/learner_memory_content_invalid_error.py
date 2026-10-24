from shifu.shared.core.domain.errors import ValidationError


class LearnerMemoryContentInvalidError(ValidationError):
    message: str = 'O texto da memória deve ter entre 1 e 280 caracteres.'
