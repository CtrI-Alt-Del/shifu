from shifu.shared.core.domain.errors import AppError, ValidationError
from shifu.shared.core.domain.structures.structure import structure


@structure
class NonEmptyText:
    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or not self.value.strip():
            raise ValidationError
        object.__setattr__(self, 'value', self.value.strip())

    @classmethod
    def create(
        cls, value: str, *, error_type: type[AppError] = ValidationError
    ) -> 'NonEmptyText':
        try:
            return cls(value=value)
        except ValidationError as error:
            raise error_type() from error
