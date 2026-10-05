from shifu.shared.core.domain.errors import AppError, ValidationError
from shifu.shared.core.domain.structures.structure import structure


@structure
class BoundedInteger:
    value: int
    minimum: int = 0
    maximum: int | None = None

    def __post_init__(self) -> None:
        if type(self.value) is not int or type(self.minimum) is not int:
            raise ValidationError
        if self.value < self.minimum:
            raise ValidationError
        if self.maximum is not None and (
            type(self.maximum) is not int
            or self.maximum < self.minimum
            or self.value > self.maximum
        ):
            raise ValidationError

    @classmethod
    def create(
        cls,
        value: int,
        *,
        minimum: int = 0,
        maximum: int | None = None,
        error_type: type[AppError] = ValidationError,
    ) -> 'BoundedInteger':
        try:
            return cls(value=value, minimum=minimum, maximum=maximum)
        except ValidationError as error:
            raise error_type() from error
