from shifu.intelligence.core.domain.enums.planning_question_kind import (
    PlanningQuestionKind,
)
from shifu.intelligence.core.domain.errors.planning_answers_invalid_error import (
    PlanningAnswersInvalidError,
)
from shifu.intelligence.core.domain.structures.planning_option import PlanningOption
from shifu.shared.core.domain.structures import structure

MIN_OPTIONS = 2
MAX_OPTIONS = 6


@structure
class PlanningQuestion:
    id: str
    text: str
    kind: PlanningQuestionKind
    options: tuple[PlanningOption, ...]

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.text.strip():
            raise ValueError('A question needs an identifier and a text.')
        regular = [option for option in self.options if not option.exclusive]
        exclusive = [option for option in self.options if option.exclusive]
        if not MIN_OPTIONS <= len(regular) <= MAX_OPTIONS:
            raise ValueError('A question needs between two and six options.')
        if len(exclusive) > 1:
            raise ValueError('A question accepts at most one exclusive option.')
        identifiers = [option.id for option in self.options]
        texts = [option.text.casefold().strip() for option in self.options]
        if len(set(identifiers)) != len(identifiers) or len(set(texts)) != len(texts):
            raise ValueError('Options must be unique.')

    @property
    def exclusive_option_id(self) -> str | None:
        return next((option.id for option in self.options if option.exclusive), None)

    def validate_selection(self, option_ids: tuple[str, ...]) -> None:
        known = {option.id for option in self.options}
        if not option_ids or len(set(option_ids)) != len(option_ids):
            raise PlanningAnswersInvalidError(
                'Cada pergunta precisa de uma seleção sem alternativas repetidas.'
            )
        if any(option_id not in known for option_id in option_ids):
            raise PlanningAnswersInvalidError(
                'Uma das alternativas selecionadas não pertence à pergunta.'
            )
        if self.kind is PlanningQuestionKind.SINGLE and len(option_ids) != 1:
            raise PlanningAnswersInvalidError(
                'Perguntas de escolha única aceitam exatamente uma alternativa.'
            )
        exclusive = self.exclusive_option_id
        if exclusive is not None and exclusive in option_ids and len(option_ids) > 1:
            raise PlanningAnswersInvalidError(
                '"Não sei" não pode ser combinada com outras alternativas.'
            )

    def selected_texts(self, option_ids: tuple[str, ...]) -> tuple[str, ...]:
        by_id = {option.id: option.text for option in self.options}
        return tuple(by_id[option_id] for option_id in option_ids if option_id in by_id)
