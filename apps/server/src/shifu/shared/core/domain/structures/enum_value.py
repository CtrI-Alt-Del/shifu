from enum import StrEnum

from shifu.shared.core.domain.errors import AppError, ValidationError
from shifu.shared.core.domain.structures.structure import structure


@structure
class EnumValue[EnumType: StrEnum]:
    value: EnumType
    enum_type: type[EnumType]

    def __post_init__(self) -> None:
        if not isinstance(self.value, self.enum_type):
            raise ValidationError

    @staticmethod
    def create[ValueType: StrEnum](
        value: ValueType,
        enum_type: type[ValueType],
        *,
        error_type: type[AppError] = ValidationError,
    ) -> 'EnumValue[ValueType]':
        try:
            return EnumValue(value=value, enum_type=enum_type)
        except ValidationError as error:
            raise error_type() from error
