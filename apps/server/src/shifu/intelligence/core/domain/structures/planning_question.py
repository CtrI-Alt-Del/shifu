from shifu.intelligence.core.domain.enums.planning_question_kind import (
    PlanningQuestionKind,
)
from shifu.intelligence.core.domain.errors.planning_answers_invalid_error import (
    PlanningAnswersInvalidError,
)
from shifu.intelligence.core.domain.structures.planning_option import (
    OTHER_TEXT_MAX_LENGTH,
    PlanningOption,
)
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
        regular = [
            option
            for option in self.options
            if not option.exclusive and not option.open
        ]
        exclusive = [option for option in self.options if option.exclusive]
        open_options = [option for option in self.options if option.open]
        if not MIN_OPTIONS <= len(regular) <= MAX_OPTIONS:
            raise ValueError('A question needs between two and six options.')
        if len(exclusive) > 1:
            raise ValueError('A question accepts at most one exclusive option.')
        if len(open_options) > 1:
            raise ValueError('A question accepts at most one open option.')
        identifiers = [option.id for option in self.options]
        texts = [option.text.casefold().strip() for option in self.options]
        if len(set(identifiers)) != len(identifiers) or len(set(texts)) != len(texts):
            raise ValueError('Options must be unique.')

    @property
    def exclusive_option_id(self) -> str | None:
        return next((option.id for option in self.options if option.exclusive), None)

    @property
    def open_option_id(self) -> str | None:
        return next((option.id for option in self.options if option.open), None)

    def validate_selection(
        self, option_ids: tuple[str, ...], other_text: str | None = None
    ) -> None:
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
        open_option = self.open_option_id
        if open_option is None or open_option not in option_ids:
            if other_text is not None:
                raise PlanningAnswersInvalidError(
                    'Uma resposta aberta exige a alternativa "Outro".'
                )
            return
        if other_text is None or not other_text.strip():
            raise PlanningAnswersInvalidError('Descreva a sua resposta em "Outro".')
        if len(other_text) > OTHER_TEXT_MAX_LENGTH:
            raise PlanningAnswersInvalidError(
                'A resposta em "Outro" aceita até 200 caracteres.'
            )

    def selected_texts(self, option_ids: tuple[str, ...]) -> tuple[str, ...]:
        # The open option is represented by the learner's text, not by its label.
        by_id = {option.id: option.text for option in self.options if not option.open}
        return tuple(by_id[option_id] for option_id in option_ids if option_id in by_id)
