from datetime import datetime

from shifu.shared.core.domain.errors import AppError, ValidationError
from shifu.shared.core.domain.structures.structure import structure


@structure
class AwareTimestamp:
    value: datetime

    def __post_init__(self) -> None:
        if (
            type(self.value) is not datetime
            or self.value.tzinfo is None
            or self.value.utcoffset() is None
        ):
            raise ValidationError

    @classmethod
    def create(
        cls, value: datetime, *, error_type: type[AppError] = ValidationError
    ) -> 'AwareTimestamp':
        try:
            return cls(value=value)
        except ValidationError as error:
            raise error_type() from error
