from shifu.intelligence.core.domain.structures.planning_question import (
    PlanningQuestion,
)
from shifu.shared.core.domain.structures import structure


@structure
class PlanningAnsweredQuestion:
    question: PlanningQuestion
    option_ids: tuple[str, ...]
    other_text: str | None = None

    def __post_init__(self) -> None:
        self.question.validate_selection(self.option_ids, self.other_text)

    @property
    def selected_texts(self) -> tuple[str, ...]:
        return self.question.selected_texts(self.option_ids)

    @property
    def answer_texts(self) -> tuple[str, ...]:
        """The selected alternatives followed by the learner's own text."""
        if self.other_text is None:
            return self.selected_texts
        return (*self.selected_texts, self.other_text)


@structure
class PlanningAnsweredBatch:
    batch_id: str
    items: tuple[PlanningAnsweredQuestion, ...]

    def __post_init__(self) -> None:
        if not self.batch_id.strip() or not self.items:
            raise ValueError('An answered batch needs an identifier and answers.')
        identifiers = [item.question.id for item in self.items]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError('An answered batch cannot repeat a question.')
