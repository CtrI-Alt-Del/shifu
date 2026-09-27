from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty

from .code_rubric_criterion import RUBRIC_LEVELS


@structure
class CodeLevelObservation:
    id: str
    level: int
    evidence: str
    interpretation_limit: str

    def __post_init__(self) -> None:
        for value in (self.id, self.evidence, self.interpretation_limit):
            require_non_empty(value, InvalidActivityError)
        if self.level not in RUBRIC_LEVELS:
            raise InvalidActivityError


@structure
class CodeInconclusiveObservation:
    id: str
    text: str

    def __post_init__(self) -> None:
        for value in (self.id, self.text):
            require_non_empty(value, InvalidActivityError)


@structure
class CodeConceptCriterion:
    concept_id: str
    description: str
    level_observations: tuple[CodeLevelObservation, ...]
    inconclusive_observation: CodeInconclusiveObservation

    def __post_init__(self) -> None:
        for value in (self.concept_id, self.description):
            require_non_empty(value, InvalidActivityError)
        if (
            tuple(sorted(item.level for item in self.level_observations))
            != RUBRIC_LEVELS
            or len({item.id for item in self.level_observations}) != 5
            or self.inconclusive_observation.id
            in {item.id for item in self.level_observations}
        ):
            raise InvalidActivityError
