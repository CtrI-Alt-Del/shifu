from typing import ClassVar

from sqlalchemy import func, select

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceConceptCriterion,
    ChoiceOption,
    CodeInconclusiveComment,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    EvaluationRule,
    ImageChoiceOption,
    ImageChoiceQuestion,
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


class ImageChoiceActivityFixture:
    """Single choice, image choice and single choice in the seeded Competency.

    The image question has four options in this order: raw, translucent,
    caramelized (the correct one) and burnt. Weights are 30, 40 and 30.
    """

    ACTIVITY_ID: ClassVar[str] = '01SHF000000000000000000210'
    CONCEPT_ID: ClassVar[str] = '01SHF000000000000000000048'
    IMAGE_QUESTION_KEY: ClassVar[str] = 'image-1'
    PROMPT: ClassVar[str] = 'Qual destas cebolas está caramelizada?'
    OPTION_KEYS: ClassVar[tuple[str, ...]] = (
        'opt-7c1e94a05d32',
        'opt-b82f6d1e4a97',
        'opt-1d5a0e83f6c4',
        'opt-e9370b2c58d1',
    )
    CORRECT_OPTION_KEY: ClassVar[str] = OPTION_KEYS[2]
    IMAGE_PATHS: ClassVar[tuple[str, ...]] = (
        '/curriculum/images/2d165276ed215938.webp',
        '/curriculum/images/51de9b1cc23dd653.webp',
        '/curriculum/images/5c8a6a6b47848a6f.webp',
        '/curriculum/images/655fecc77404ac40.webp',
    )
    DESCRIPTIONS: ClassVar[tuple[str, ...]] = (
        'Fatias brancas e firmes, sem brilho, espalhadas na frigideira escura.',
        'Fatias macias e quase transparentes, com brilho úmido e sem cor.',
        'Fios macios de cor de mel escuro, com brilho de calda.',
        'Pedaços encolhidos e secos, de cor quase preta.',
    )
    FEEDBACKS: ClassVar[tuple[str, ...]] = (
        'Essa cebola ainda está crua.',
        'Essa cebola já amoleceu, mas ainda não ganhou cor.',
        'Essa cebola chegou ao ponto de caramelização.',
        'Essa cebola passou do ponto e queimou.',
    )
    CORRECT_EXPLANATION: ClassVar[str] = 'Explicação privada de acerto da imagem.'
    INCORRECT_EXPLANATION: ClassVar[str] = 'Explicação privada de erro da imagem.'
    SUBMISSION_KEY: ClassVar[str] = '6b1c0d2e-4f3a-4b5c-9d8e-7f6a5b4c3d2e'

    @staticmethod
    def _choices() -> tuple[SingleChoiceQuestion, SingleChoiceQuestion]:
        first, second = (
            SingleChoiceQuestion(
                key=key,
                prompt='Escolha',
                options=(
                    ChoiceOption(key='a', text='A', is_correct=True),
                    ChoiceOption(key='b', text='B', is_correct=False),
                ),
                correct_explanation='Certo',
                incorrect_explanation='Errado',
            )
            for key in ('q1', 'q3')
        )
        return first, second

    @staticmethod
    def image_question(*, concept_id: str | None = None) -> ImageChoiceQuestion:
        return ImageChoiceQuestion(
            key=ImageChoiceActivityFixture.IMAGE_QUESTION_KEY,
            prompt=ImageChoiceActivityFixture.PROMPT,
            options=tuple(
                ImageChoiceOption(
                    key=key,
                    image_path=path,
                    description=description,
                    is_correct=key == ImageChoiceActivityFixture.CORRECT_OPTION_KEY,
                    feedback=feedback,
                )
                for key, path, description, feedback in zip(
                    ImageChoiceActivityFixture.OPTION_KEYS,
                    ImageChoiceActivityFixture.IMAGE_PATHS,
                    ImageChoiceActivityFixture.DESCRIPTIONS,
                    ImageChoiceActivityFixture.FEEDBACKS,
                    strict=True,
                )
            ),
            correct_explanation=ImageChoiceActivityFixture.CORRECT_EXPLANATION,
            incorrect_explanation=ImageChoiceActivityFixture.INCORRECT_EXPLANATION,
            concept_criteria=(
                ChoiceConceptCriterion(
                    concept_id=concept_id or ImageChoiceActivityFixture.CONCEPT_ID,
                    criterion='Reconhece o ponto de cocção.',
                    examples='Cebola macia e escura.',
                    limits='Não mede a execução.',
                    correct_score=100,
                    incorrect_score=0,
                ),
            ),
        )

    @staticmethod
    def activity(*, concept_id: str | None = None) -> Activity:
        first, last = ImageChoiceActivityFixture._choices()
        return Activity.create(
            id=ImageChoiceActivityFixture.ACTIVITY_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Ponto de cocção',
            objective='Reconhecer o ponto de cocção pela aparência.',
            questions=(
                first,
                ImageChoiceActivityFixture.image_question(concept_id=concept_id),
                last,
            ),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                    CorrectnessEvaluationPart(
                        question_key=ImageChoiceActivityFixture.IMAGE_QUESTION_KEY,
                        weight_percentage=40,
                    ),
                    CorrectnessEvaluationPart(question_key='q3', weight_percentage=30),
                ),
            ),
        )

    @staticmethod
    def code_activity() -> Activity:
        """The image question beside a React question, which routes to AgentOS."""
        first, _ = ImageChoiceActivityFixture._choices()
        code = ReactQuestion(
            key='q3',
            prompt='Renderize o componente React',
            initial_files=(
                ReactInitialFile(
                    path='src/App.jsx',
                    content='export default function App() { return null }',
                    editable=True,
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
            additional_file_policy=None,
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
            id=ImageChoiceActivityFixture.ACTIVITY_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Ponto de cocção com código',
            objective='Reconhecer o ponto de cocção e renderizar um componente.',
            questions=(first, ImageChoiceActivityFixture.image_question(), code),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                    CorrectnessEvaluationPart(
                        question_key=ImageChoiceActivityFixture.IMAGE_QUESTION_KEY,
                        weight_percentage=40,
                    ),
                    CodeRubricEvaluationPart(
                        question_key='q3', weight_percentage=30, criteria=(criterion,)
                    ),
                ),
            ),
        )

    @staticmethod
    def activity_path(activity_id: str | None = None) -> str:
        return (
            f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
            f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
            f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
            f'/activities/{activity_id or ImageChoiceActivityFixture.ACTIVITY_ID}'
        )

    @staticmethod
    def preview_path() -> str:
        return (
            f'{ImageChoiceActivityFixture.activity_path()}'
            f'/questions/{ImageChoiceActivityFixture.IMAGE_QUESTION_KEY}'
            '/preliminary-evaluations'
        )

    @staticmethod
    def attempts_path() -> str:
        return f'{ImageChoiceActivityFixture.activity_path()}/attempts'

    @staticmethod
    def image_answer(*option_keys: str) -> dict[str, object]:
        return {
            'kind': 'image_choice',
            'question_key': ImageChoiceActivityFixture.IMAGE_QUESTION_KEY,
            'selected_option_keys': list(option_keys),
        }

    @staticmethod
    def preview(revision: str, *option_keys: str) -> dict[str, object]:
        return {
            'activity_revision': revision,
            'answer': ImageChoiceActivityFixture.image_answer(*option_keys),
        }

    @staticmethod
    def submission(
        revision: str,
        *option_keys: str,
        submission_key: str | None = None,
    ) -> dict[str, object]:
        return {
            'submission_key': submission_key
            or ImageChoiceActivityFixture.SUBMISSION_KEY,
            'activity_revision': revision,
            'answers': [
                {
                    'kind': 'single_choice',
                    'question_key': 'q1',
                    'selected_option_keys': ['a'],
                },
                ImageChoiceActivityFixture.image_answer(*option_keys),
                {
                    'kind': 'single_choice',
                    'question_key': 'q3',
                    'selected_option_keys': ['a'],
                },
            ],
        }

    @staticmethod
    def write_counts(database: PostgresDatabase) -> tuple[int, ...]:
        """Attempts, evaluations, observations and outbox events, in this order."""
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
