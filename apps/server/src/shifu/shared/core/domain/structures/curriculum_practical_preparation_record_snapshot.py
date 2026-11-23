from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumPracticalPreparationRecordSnapshot:
    key: str
    label: str
    must_show: str

    def __post_init__(self) -> None:
        for name in ('key', 'label', 'must_show'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )
