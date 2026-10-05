from datetime import datetime

from shifu.shared.core.domain.errors import AppError, ValidationError
from shifu.shared.core.domain.structures.aware_timestamp import AwareTimestamp
from shifu.shared.core.domain.structures.structure import structure


@structure
class ChronologicalPeriod:
    started_at: datetime
    ended_at: datetime

    def __post_init__(self) -> None:
        AwareTimestamp(value=self.started_at)
        AwareTimestamp(value=self.ended_at)
        if self.ended_at < self.started_at:
            raise ValidationError

    @classmethod
    def create(
        cls,
        started_at: datetime,
        ended_at: datetime,
        *,
        error_type: type[AppError] = ValidationError,
    ) -> 'ChronologicalPeriod':
        try:
            return cls(started_at=started_at, ended_at=ended_at)
        except ValidationError as error:
            raise error_type() from error
