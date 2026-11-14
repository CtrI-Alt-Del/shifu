from shifu.intelligence.core.domain.structures.planning_question import (
    PlanningQuestion,
)
from shifu.shared.core.domain.structures import structure

MIN_QUESTIONS = 1
MAX_QUESTIONS = 4


@structure
class PlanningQuestionBatch:
    id: str
    questions: tuple[PlanningQuestion, ...]

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError('A batch needs an identifier.')
        if not MIN_QUESTIONS <= len(self.questions) <= MAX_QUESTIONS:
            raise ValueError('A batch needs between one and four questions.')
        identifiers = [question.id for question in self.questions]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError('Questions of a batch must be unique.')

    def find_question(self, question_id: str) -> PlanningQuestion | None:
        return next(
            (question for question in self.questions if question.id == question_id),
            None,
        )
