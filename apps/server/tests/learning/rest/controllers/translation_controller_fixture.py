from typing import ClassVar

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    CorrectnessEvaluationPart,
    EvaluationRule,
    SingleChoiceQuestion,
    TranslationInconclusiveComment,
    TranslationQuestion,
    TranslationRubricComment,
    TranslationRubricCriterion,
    TranslationRubricEvaluationPart,
)
from shifu.shared.database.seed_data import (
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
)

_SEMANTIC_KEY = 'semantic_preservation'
_GRAMMAR_KEY = 'grammatical_adequacy'


class TranslationControllerFixture:
    ACTIVITY_ID: ClassVar[str] = '01SHF000000000000000000094'
    PROMPT: ClassVar[str] = 'Traduza o texto a seguir.'
    SOURCE_LANGUAGE: ClassVar[str] = 'pt-BR'
    TARGET_LANGUAGE: ClassVar[str] = 'en-US'
    SOURCE_TEXT: ClassVar[str] = 'Bom dia'
    REFERENCE_TRANSLATION: ClassVar[str] = 'Good morning'
    SUBMITTED_TEXT: ClassVar[str] = 'Good morning'

    @staticmethod
    def _rubric_criterion(key: str, weight: int) -> TranslationRubricCriterion:
        return TranslationRubricCriterion(
            key=key,
            name=key.replace('_', ' ').title(),
            description=f'Evaluate {key}.',
            weight_percentage=weight,
            required=True,
            fixed_comments=tuple(
                TranslationRubricComment(
                    id=f'{key}-{level}', level=level, text=f'Private comment {level}'
                )
                for level in (0, 25, 50, 75, 100)
            ),
            inconclusive_comment=TranslationInconclusiveComment(
                id=f'{key}-unknown', text='Private inconclusive comment'
            ),
        )

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
        question = TranslationQuestion(
            key='q3',
            prompt=TranslationControllerFixture.PROMPT,
            source_language=TranslationControllerFixture.SOURCE_LANGUAGE,
            target_language=TranslationControllerFixture.TARGET_LANGUAGE,
            source_text=TranslationControllerFixture.SOURCE_TEXT,
            reference_translations=(
                TranslationControllerFixture.REFERENCE_TRANSLATION,
            ),
            concept_criteria=(),
        )
        return Activity.create(
            id=TranslationControllerFixture.ACTIVITY_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Atividade de tradução',
            objective='Praticar tradução de texto',
            questions=(*choices, question),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                    CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                    TranslationRubricEvaluationPart(
                        question_key='q3',
                        weight_percentage=40,
                        criteria=(
                            TranslationControllerFixture._rubric_criterion(
                                _SEMANTIC_KEY, 70
                            ),
                            TranslationControllerFixture._rubric_criterion(
                                _GRAMMAR_KEY, 30
                            ),
                        ),
                    ),
                )
            ),
        )

    @staticmethod
    def activity_path() -> str:
        return (
            f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
            f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
            f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
            f'/activities/{TranslationControllerFixture.ACTIVITY_ID}'
        )

    @staticmethod
    def attempts_path() -> str:
        return f'{TranslationControllerFixture.activity_path()}/attempts'

    @staticmethod
    def submission(revision: str, *, text: str | None = None) -> dict[str, object]:
        return {
            'submission_key': '1c7e9a53-6b42-4e88-9d2d-5ca293c0f123',
            'activity_revision': revision,
            'answers': [
                {
                    'kind': 'single_choice',
                    'question_key': key,
                    'selected_option_keys': ['a'],
                }
                for key in ('q1', 'q2')
            ]
            + [
                {
                    'kind': 'translation',
                    'question_key': 'q3',
                    'text': text
                    if text is not None
                    else (TranslationControllerFixture.SUBMITTED_TEXT),
                }
            ],
        }
