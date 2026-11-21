from typing import ClassVar

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    CorrectnessEvaluationPart,
    EvaluationRule,
    PairMatchingItem,
    PairMatchingPair,
    PairMatchingQuestion,
    SingleChoiceQuestion,
)
from shifu.shared.database.seed_data import (
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
)

_WORDS = ('dog', 'house', 'water')
_TRANSLATIONS = ('cachorro', 'casa', 'agua')


class PairMatchingControllerFixture:
    """A learning Activity with two choice questions and one pair question.

    Pair ``i`` joins ``word-i`` with ``translation-i``. The translation list is
    displayed rotated by one position, so its order never mirrors the key.
    """

    ACTIVITY_ID: ClassVar[str] = '01SHF000000000000000000095'
    PROMPT: ClassVar[str] = 'Associe cada palavra a sua traducao'
    FULL_EXPLANATION: ClassVar[str] = 'Todos os pares estao corretos.'
    PARTIAL_EXPLANATION: ClassVar[str] = 'Alguns pares estao corretos.'
    INCORRECT_EXPLANATION: ClassVar[str] = 'Nenhum par esta correto.'
    SUBMISSION_KEY: ClassVar[str] = '5a0b9f1e-3c2d-4e5f-8a7b-6c1d2e3f4a5b'

    @staticmethod
    def activity() -> Activity:
        choices = tuple(
            SingleChoiceQuestion(
                key=f'q{index}',
                prompt='Escolha',
                options=(
                    ChoiceOption(key='a', text='A', is_correct=True),
                    ChoiceOption(key='b', text='B', is_correct=False),
                ),
                correct_explanation='Certo',
                incorrect_explanation='Errado',
            )
            for index in (1, 2)
        )
        question = PairMatchingQuestion(
            key='q3',
            prompt=PairMatchingControllerFixture.PROMPT,
            source_language='en',
            target_language='pt-BR',
            words=tuple(
                PairMatchingItem(key=f'word-{index}', text=_WORDS[index])
                for index in range(3)
            ),
            translations=tuple(
                PairMatchingItem(
                    key=f'translation-{(index + 1) % 3}',
                    text=_TRANSLATIONS[(index + 1) % 3],
                )
                for index in range(3)
            ),
            correct_pairs=tuple(
                PairMatchingPair(
                    word_key=f'word-{index}', translation_key=f'translation-{index}'
                )
                for index in range(3)
            ),
            full_explanation=PairMatchingControllerFixture.FULL_EXPLANATION,
            partial_explanation=PairMatchingControllerFixture.PARTIAL_EXPLANATION,
            incorrect_explanation=PairMatchingControllerFixture.INCORRECT_EXPLANATION,
        )
        return Activity.create(
            id=PairMatchingControllerFixture.ACTIVITY_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Atividade de pares',
            objective='Associar palavras e traducoes',
            questions=(*choices, question),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                    CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                    CorrectnessEvaluationPart(question_key='q3', weight_percentage=40),
                )
            ),
        )

    @staticmethod
    def activity_path() -> str:
        return (
            f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
            f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
            f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
            f'/activities/{PairMatchingControllerFixture.ACTIVITY_ID}'
        )

    @staticmethod
    def attempts_path() -> str:
        return f'{PairMatchingControllerFixture.activity_path()}/attempts'

    @staticmethod
    def preview_path() -> str:
        return (
            f'{PairMatchingControllerFixture.activity_path()}'
            '/questions/q3/preliminary-evaluations'
        )

    @staticmethod
    def pairs(*translation_indexes: int) -> list[dict[str, str]]:
        return [
            {
                'word_key': f'word-{word_index}',
                'translation_key': f'translation-{translation_index}',
            }
            for word_index, translation_index in enumerate(translation_indexes)
        ]

    @staticmethod
    def answer(*translation_indexes: int) -> dict[str, object]:
        return {
            'kind': 'pair_matching',
            'question_key': 'q3',
            'pairs': PairMatchingControllerFixture.pairs(*translation_indexes),
        }

    @staticmethod
    def submission(
        revision: str, *translation_indexes: int, key: str | None = None
    ) -> dict[str, object]:
        return {
            'submission_key': key or PairMatchingControllerFixture.SUBMISSION_KEY,
            'activity_revision': revision,
            'answers': [
                {
                    'kind': 'single_choice',
                    'question_key': question_key,
                    'selected_option_keys': ['a'],
                }
                for question_key in ('q1', 'q2')
            ]
            + [
                PairMatchingControllerFixture.answer(
                    *(translation_indexes or (0, 1, 2))
                )
            ],
        }
