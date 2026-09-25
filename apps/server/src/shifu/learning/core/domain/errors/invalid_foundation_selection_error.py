from shifu.shared.core.domain.errors import ValidationError


class InvalidFoundationSelectionError(ValidationError):
    message: str = 'A base selecionada não é uma base direta desta habilidade.'
