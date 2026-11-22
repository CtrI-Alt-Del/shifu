from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class PracticePhotoRecord:
    key: str
    label: str
    must_show: str

    def __post_init__(self) -> None:
        for name in ('key', 'label', 'must_show'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )
