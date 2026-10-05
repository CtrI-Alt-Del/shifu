from decimal import Decimal

from shifu.shared.core.domain.errors import AppError, ValidationError
from shifu.shared.core.domain.structures.structure import structure


def _numeric_percentage(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValidationError
    numeric = Decimal(str(value))
    if numeric < Decimal('0') or numeric > Decimal('100'):
        raise ValidationError
    return numeric


@structure
class Percentage:
    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, 'value', _numeric_percentage(self.value))

    @classmethod
    def create(
        cls, value: object, *, error_type: type[AppError] = ValidationError
    ) -> 'Percentage':
        try:
            return cls(value=_numeric_percentage(value))
        except ValidationError as error:
            raise error_type() from error
