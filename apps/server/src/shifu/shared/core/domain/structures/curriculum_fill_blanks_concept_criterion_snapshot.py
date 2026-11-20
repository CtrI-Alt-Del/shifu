from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText


@structure
class CurriculumFillBlanksConceptCriterionSnapshot:
    concept_id: str
    criterion: str
    examples: str
    limits: str
    blank_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ('concept_id', 'criterion', 'examples', 'limits'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )
        if not self.blank_keys or len(self.blank_keys) != len(set(self.blank_keys)):
            raise ValidationError
