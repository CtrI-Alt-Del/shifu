from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumPracticalPreparationInsufficiencyRuleSnapshot:
    record_key: str
    criterion_keys: tuple[str, ...]
    comment: str

    def __post_init__(self) -> None:
        for name in ('record_key', 'comment'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )
        for key in self.criterion_keys:
            NonEmptyText.create(key, error_type=ValidationError)
        if not self.criterion_keys or len(self.criterion_keys) != len(
            set(self.criterion_keys)
        ):
            raise ValidationError
