from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText


@structure
class CurriculumFillBlanksSegmentSnapshot:
    text: str | None = None
    blank_key: str | None = None

    def __post_init__(self) -> None:
        if (self.text is None) == (self.blank_key is None):
            raise ValidationError

        if self.blank_key is not None:
            object.__setattr__(
                self,
                'blank_key',
                NonEmptyText.create(self.blank_key, error_type=ValidationError).value,
            )
