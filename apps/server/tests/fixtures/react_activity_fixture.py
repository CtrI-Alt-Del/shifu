from typing import ClassVar

from sqlalchemy import func, select

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    CodeInconclusiveComment,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    EvaluationRule,
    ReactAdditionalFilePolicy,
    ReactDependency,
    ReactInitialFile,
    ReactPermittedCommand,
    ReactQuestion,
    SingleChoiceQuestion,
)
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


class ReactControllerFixture:
    ACTIVITY_ID: ClassVar[str] = '01SHF000000000000000000092'
    PROMPT: ClassVar[str] = 'Renderize o componente React'
    INITIAL_SOURCE: ClassVar[str] = 'export default function App() { return null }'
    SUBMITTED_SOURCE: ClassVar[str] = (
        'export default function App() { return <h1>Oi</h1> }'
    )
    FIXED_HTML: ClassVar[str] = '<div id="root"></div>'
    ADDITIONAL_SOURCE: ClassVar[str] = 'export const title = "Oi"'

    @staticmethod
    def activity(*, with_policy: bool = True) -> Activity:
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
        question = ReactQuestion(
            key='q3',
            prompt=ReactControllerFixture.PROMPT,
            initial_files=(
                ReactInitialFile(
                    path='src/App.jsx',
                    content=ReactControllerFixture.INITIAL_SOURCE,
                    editable=True,
                ),
                ReactInitialFile(
                    path='index.html',
                    content=ReactControllerFixture.FIXED_HTML,
                    editable=False,
                ),
            ),
            entrypoint='src/App.jsx',
            fixed_dependencies=(ReactDependency(name='react', version='19.2.0'),),
            permitted_commands=(
                ReactPermittedCommand(
                    id='dev', executable='npm', arguments=('run', 'dev')
                ),
            ),
            concept_criteria=(),
            additional_file_policy=(
                ReactAdditionalFilePolicy(
                    allowed_directories=('src/components',),
                    allowed_extensions=('.jsx', '.js'),
                    max_files=2,
                )
                if with_policy
                else None
            ),
        )
        criterion = CodeRubricCriterion(
            key='correctness',
            name='Correção',
            description='Renderiza o componente',
            weight_percentage=100,
            required=True,
            fixed_comments=tuple(
                CodeRubricComment(
                    id=f'comment-{level}', level=level, text=f'Fixed comment {level}'
                )
                for level in (0, 25, 50, 75, 100)
            ),
            inconclusive_comment=CodeInconclusiveComment(
                id='unknown', text='Inconclusivo'
            ),
        )
        return Activity.create(
            id=ReactControllerFixture.ACTIVITY_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Atividade React',
            objective='Aprender React',
            questions=(*choices, question),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                    CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                    CodeRubricEvaluationPart(
                        question_key='q3', weight_percentage=40, criteria=(criterion,)
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
            f'/activities/{ReactControllerFixture.ACTIVITY_ID}'
        )

    @staticmethod
    def answer_files() -> list[dict[str, str]]:
        return [
            {'path': 'src/App.jsx', 'content': ReactControllerFixture.SUBMITTED_SOURCE},
            {
                'path': 'src/components/title.js',
                'content': ReactControllerFixture.ADDITIONAL_SOURCE,
            },
        ]

    @staticmethod
    def composed_files() -> list[dict[str, str]]:
        return [
            {'path': 'index.html', 'content': ReactControllerFixture.FIXED_HTML},
            *ReactControllerFixture.answer_files(),
        ]

    @staticmethod
    def submission(revision: str) -> dict[str, object]:
        return {
            'submission_key': 'e9aa7b85-c95b-4319-b98e-5ca293c09f61',
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
                    'kind': 'react',
                    'question_key': 'q3',
                    'files': ReactControllerFixture.answer_files(),
                }
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
