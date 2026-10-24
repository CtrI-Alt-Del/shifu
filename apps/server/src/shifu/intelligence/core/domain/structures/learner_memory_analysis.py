from shifu.intelligence.core.domain.structures.learner_memory_statement import (
    LearnerMemoryStatement,
)
from shifu.shared.core.domain.structures import structure


@structure
class LearnerMemoryAnalysis:
    statements: tuple[LearnerMemoryStatement, ...]
    sentence_count: int

    def __post_init__(self) -> None:
        if self.sentence_count < len(self.statements):
            raise ValueError('Invalid learner memory analysis')

    @property
    def statement_only(self) -> bool:
        return self.sentence_count > 0 and len(self.statements) == self.sentence_count
