from shifu.shared.core.domain.errors import ValidationError


class InvalidAppearanceError(ValidationError):
    message: str = 'Selecione uma aparência válida.'
