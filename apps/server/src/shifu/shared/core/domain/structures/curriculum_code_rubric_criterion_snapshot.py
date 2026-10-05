from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumCodeRubricCommentSnapshot:
    id: str
    level: int
    text: str


@structure
class CurriculumCodeInconclusiveCommentSnapshot:
    id: str
    text: str


@structure
class CurriculumCodeRubricCriterionSnapshot:
    key: str
    name: str
    description: str
    weight_percentage: int
    required: bool
    fixed_comments: tuple[CurriculumCodeRubricCommentSnapshot, ...]
    inconclusive_comment: CurriculumCodeInconclusiveCommentSnapshot

    def __post_init__(self) -> None:
        for value in (self.key, self.name, self.description):
            NonEmptyText.create(value, error_type=ValidationError)
        if (
            not 0 <= self.weight_percentage <= 100
            or tuple(sorted(item.level for item in self.fixed_comments))
            != (0, 25, 50, 75, 100)
            or len({item.id for item in self.fixed_comments}) != 5
            or self.inconclusive_comment.id in {item.id for item in self.fixed_comments}
        ):
            raise ValidationError
