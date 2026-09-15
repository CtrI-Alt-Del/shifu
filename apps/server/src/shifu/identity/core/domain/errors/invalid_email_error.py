from shifu.shared.core.domain.errors import ValidationError


class InvalidEmailError(ValidationError):
    message: str = 'O e-mail informado é inválido.'
