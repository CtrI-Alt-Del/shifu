from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.shared.core.domain.structures import NonEmptyText, structure

RUBRIC_LEVELS = (0, 25, 50, 75, 100)


@structure
class CodeRubricComment:
    id: str
    level: int
    text: str

    def __post_init__(self) -> None:
        for value in (self.id, self.text):
            NonEmptyText.create(value, error_type=InvalidEvaluationRuleError)
        if self.level not in RUBRIC_LEVELS:
            raise InvalidEvaluationRuleError


@structure
class CodeInconclusiveComment:
    id: str
    text: str

    def __post_init__(self) -> None:
        for value in (self.id, self.text):
            NonEmptyText.create(value, error_type=InvalidEvaluationRuleError)


@structure
class CodeRubricCriterion:
    key: str
    name: str
    description: str
    weight_percentage: int
    required: bool
    fixed_comments: tuple[CodeRubricComment, ...]
    inconclusive_comment: CodeInconclusiveComment

    def __post_init__(self) -> None:
        for value in (self.key, self.name, self.description):
            NonEmptyText.create(value, error_type=InvalidEvaluationRuleError)
        if (
            not 0 <= self.weight_percentage <= 100
            or tuple(sorted(item.level for item in self.fixed_comments))
            != RUBRIC_LEVELS
            or len({item.id for item in self.fixed_comments}) != 5
            or self.inconclusive_comment.id in {item.id for item in self.fixed_comments}
        ):
            raise InvalidEvaluationRuleError
