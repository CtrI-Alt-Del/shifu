from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class FillBlanksSegment:
    text: str | None = None
    blank_key: str | None = None

    def __post_init__(self) -> None:
        if (self.text is None) == (self.blank_key is None):
            raise InvalidActivityError

        if self.blank_key is not None:
            object.__setattr__(
                self,
                'blank_key',
                NonEmptyText.create(
                    self.blank_key, error_type=InvalidActivityError
                ).value,
            )
