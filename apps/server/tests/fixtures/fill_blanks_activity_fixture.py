from typing import ClassVar

from sqlalchemy import func, select

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    CorrectnessEvaluationPart,
    EvaluationRule,
    FillBlanksConceptCriterion,
    SingleChoiceQuestion,
)
from shifu.fakers.curriculum.structures import FillBlanksQuestionFaker
from shifu.learning.database.sqlalchemy.models import (
    ActivityAttemptModel,
    ActivityEvaluationModel,
    ConceptObservationModel,
)
from shifu.shared.database.seed_data import (
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from tests.fixtures.postgres_fixture import PostgresDatabase

CORRECT_PAIRS: tuple[tuple[str, str], ...] = (
    ('b1', 'w1'),
    ('b2', 'w3'),
    ('b3', 'w4'),
)
PARTIAL_PAIRS: tuple[tuple[str, str], ...] = (
    ('b1', 'w1'),
    ('b2', 'w6'),
    ('b3', 'w2'),
)


class FillBlanksActivityFixture:
    """One fill-blanks question and two single-choice ones in the seeded Competency."""

    ACTIVITY_ID: ClassVar[str] = '01SHF000000000000000000200'
    FIRST_CONCEPT_ID: ClassVar[str] = '01SHF000000000000000000048'
    SECOND_CONCEPT_ID: ClassVar[str] = '01SHF000000000000000000074'

    @staticmethod
    def activity(*, concept_id: str | None = None) -> Activity:
        fill = FillBlanksQuestionFaker.fake(
            concept_criteria=(
                FillBlanksConceptCriterion(
                    concept_id=concept_id or FillBlanksActivityFixture.FIRST_CONCEPT_ID,
                    criterion='Verb agreement',
                    examples='She goes.',
                    limits='None.',
                    blank_keys=('b1', 'b2'),
                ),
                FillBlanksConceptCriterion(
                    concept_id=FillBlanksActivityFixture.SECOND_CONCEPT_ID,
                    criterion='Time expressions',
                    examples='every day.',
                    limits='None.',
                    blank_keys=('b3',),
                ),
            )
        )
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
        return Activity.create(
            id=FillBlanksActivityFixture.ACTIVITY_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='English practice',
            objective='Practice the present simple',
            questions=(fill, *choices),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(
                        question_key='fill-1', weight_percentage=40
                    ),
                    CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                    CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                )
            ),
        )

    @staticmethod
    def activity_path() -> str:
        return (
            f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
            f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
            f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
            f'/activities/{FillBlanksActivityFixture.ACTIVITY_ID}'
        )

    @staticmethod
    def placements(*pairs: tuple[str, str]) -> list[dict[str, str]]:
        return [{'blank_key': blank, 'word_key': word} for blank, word in pairs]

    @staticmethod
    def fill_answer(*pairs: tuple[str, str]) -> dict[str, object]:
        return {
            'kind': 'fill_blanks',
            'question_key': 'fill-1',
            'placements': FillBlanksActivityFixture.placements(*pairs),
        }

    @staticmethod
    def submission(
        revision: str,
        *pairs: tuple[str, str],
        submission_key: str = 'e9aa7b85-c95b-4319-b98e-5ca293c09f61',
    ) -> dict[str, object]:
        return {
            'submission_key': submission_key,
            'activity_revision': revision,
            'answers': [
                FillBlanksActivityFixture.fill_answer(*pairs),
                {
                    'kind': 'single_choice',
                    'question_key': 'q1',
                    'selected_option_keys': ['a'],
                },
                {
                    'kind': 'single_choice',
                    'question_key': 'q2',
                    'selected_option_keys': ['b'],
                },
            ],
        }

    @staticmethod
    def write_counts(database: PostgresDatabase) -> tuple[int, ...]:
        with database.engine.connect() as connection:
            return tuple(
                connection.scalar(select(func.count()).select_from(model)) or 0
                for model in (
                    ActivityAttemptModel,
                    ActivityEvaluationModel,
                    ConceptObservationModel,
                    EventModel,
                )
            )
