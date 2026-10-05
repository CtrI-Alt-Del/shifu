from collections.abc import Iterable

from shifu.shared.core.domain.errors import AppError, ValidationError
from shifu.shared.core.domain.structures.structure import structure


@structure
class WeightDistribution:
    values: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.values or any(weight < 0 or weight > 100 for weight in self.values):
            raise ValidationError
        if sum(self.values) != 100:
            raise ValidationError

    @classmethod
    def create(
        cls, values: Iterable[int], *, error_type: type[AppError] = ValidationError
    ) -> 'WeightDistribution':
        try:
            return cls(values=tuple(values))
        except ValidationError as error:
            raise error_type() from error
