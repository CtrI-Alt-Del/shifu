import re

from shifu.shared.core.domain.errors import AppError, ValidationError
from shifu.shared.core.domain.structures.structure import structure

_EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


@structure
class EmailAddress:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().casefold()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValidationError
        object.__setattr__(self, 'value', normalized)

    @classmethod
    def create(
        cls, value: str, *, error_type: type[AppError] = ValidationError
    ) -> 'EmailAddress':
        try:
            return cls(value=value)
        except ValidationError as error:
            raise error_type() from error
