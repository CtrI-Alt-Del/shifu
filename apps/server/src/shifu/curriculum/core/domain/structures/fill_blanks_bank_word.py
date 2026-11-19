from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class FillBlanksBankWord:
    key: str
    word: str

    def __post_init__(self) -> None:
        for name in ('key', 'word'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )
