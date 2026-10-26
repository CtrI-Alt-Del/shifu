from shifu.shared.core.domain.errors import ValidationError


class InvalidTimeZoneError(ValidationError):
    message: str = 'Selecione um fuso horário válido.'
