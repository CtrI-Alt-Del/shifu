"""Describe the questions a learner sees in an activity, for the Mentor.

Only what the activity page already shows is described: prompts, options, steps and
words. Answer keys, grading rules and verified results never leave this module.
"""

from collections.abc import Iterable

from shifu.learning.core.domain.structures import (
    ChoiceActivityDetail,
    ChoiceQuestionDetail,
    FillBlanksQuestionDetail,
    ImageChoiceQuestionDetail,
    OrderingQuestionDetail,
    PairMatchingQuestionDetail,
    PracticalPreparationQuestionDetail,
    TranslationQuestionDetail,
)

_TEXT_LIMIT = 700
_KIND_LABELS = {
    'single_choice': 'escolha única',
    'multiple_selection': 'múltipla seleção',
    'ordering': 'ordenação',
    'fill_blanks': 'completar lacunas',
    'translation': 'tradução',
    'pair_matching': 'associação de pares',
    'image_choice': 'escolha de imagem',
    'practical_preparation': 'preparo prático',
}


def activity_question_facts(
    detail: ChoiceActivityDetail,
) -> tuple[tuple[str, str], ...]:
    total = len(detail.questions)
    return tuple(
        (
            'activity_questions',
            _bounded(
                f'{question.key}: questão {index} de {total} '
                f'({_KIND_LABELS.get(question.kind, "código")}): '
                f'{question.prompt}{_details(question)}'
            ),
        )
        for index, question in enumerate(detail.questions, start=1)
    )


def _details(question: object) -> str:
    if isinstance(question, ChoiceQuestionDetail):
        return _list('Opções', (option.text for option in question.options))
    if isinstance(question, ImageChoiceQuestionDetail):
        return _list('Imagens', (option.description for option in question.options))
    if isinstance(question, OrderingQuestionDetail):
        return _list('Etapas a ordenar', (step.text for step in question.steps))
    if isinstance(question, FillBlanksQuestionDetail):
        sentence = ''.join(
            segment.text if segment.text is not None else '___'
            for segment in question.segments
        )
        return f' | Frase: {sentence}' + _list(
            'Palavras', (word.word for word in question.bank)
        )
    if isinstance(question, TranslationQuestionDetail):
        return (
            f' | Traduzir de {question.source_language} para '
            f'{question.target_language}: {question.source_text}'
        )
    if isinstance(question, PairMatchingQuestionDetail):
        return _list('Palavras', (item.text for item in question.words)) + _list(
            'Traduções', (item.text for item in question.translations)
        )
    if isinstance(question, PracticalPreparationQuestionDetail):
        return _list('Orientações', question.guidance) + _list(
            'Registros pedidos', (record.label for record in question.records)
        )
    return ''


def _list(label: str, items: Iterable[str]) -> str:
    values = [item.strip() for item in items if item.strip()]
    return f' | {label}: {"; ".join(values)}' if values else ''


def _bounded(text: str) -> str:
    return text if len(text) <= _TEXT_LIMIT else f'{text[: _TEXT_LIMIT - 1]}…'
