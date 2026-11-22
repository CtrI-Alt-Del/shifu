from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

type PracticeLevel = Literal[0, 25, 50, 75, 100]

_LEVELS = (0, 25, 50, 75, 100)


@structure
class PracticeCriterionDecision:
    """Closed decision for one criterion; a null level means inconclusive."""

    key: str
    level: PracticeLevel | None
    comment_key: str | None

    def __post_init__(self) -> None:
        NonEmptyText.create(self.key, error_type=ValidationError)
        if self.level is None:
            if self.comment_key is not None:
                raise ValidationError
            return

        if self.level not in _LEVELS or self.comment_key is None:
            raise ValidationError
        NonEmptyText.create(self.comment_key, error_type=ValidationError)


@structure
class PracticeRecordDecision:
    record_key: str
    sufficient: bool

    def __post_init__(self) -> None:
        NonEmptyText.create(self.record_key, error_type=ValidationError)
        if type(self.sufficient) is not bool:
            raise ValidationError


@structure
class PracticePhotoDecisions:
    criteria: tuple[PracticeCriterionDecision, ...]
    records: tuple[PracticeRecordDecision, ...]

    def __post_init__(self) -> None:
        if len(self.criteria) != len({item.key for item in self.criteria}) or len(
            self.records
        ) != len({item.record_key for item in self.records}):
            raise ValidationError
