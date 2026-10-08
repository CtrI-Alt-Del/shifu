from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from shifu.app import FastAPIApp
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
    JavascriptInitialFile,
    JavascriptStdinQuestion,
    SingleChoiceQuestion,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.pipes import LearningPipe
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import (
    AuthenticatedUser,
    CodeCriterionDecision,
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
)
from shifu.shared.core.interfaces import CodeRubricAssessorProvider
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID,
    SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    build_development_seed,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.learning.database.sqlalchemy.models import (
    ActivityAttemptModel,
    ActivityEvaluationModel,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response


_ACTIVITY_ID = '01SHF000000000000000000091'
_QUESTION_KEY = 'q3'


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


class _NoopBroker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class _FixedCodeRubricAssessorProvider(CodeRubricAssessorProvider):
    def __init__(self) -> None:
        self.requests: list[CodeRubricAssessmentInput] = []

    def assess(self, request: CodeRubricAssessmentInput) -> CodeRubricDecisions:
        self.requests.append(request)
        return CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
            concept_levels=(),
        )


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    seed = build_development_seed()
    curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))
    learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
    with learning_database.transaction() as repositories:
        repositories.goals.add_many(list(seed.goals))
        repositories.skill_experiences.add_many(list(seed.skill_experiences))
        repositories.competency_progresses.add_many(list(seed.competency_progresses))
        repositories.activity_attempts.add_many(list(seed.activity_attempts))
        repositories.activity_evaluations.add_many(list(seed.activity_evaluations))
        experience = repositories.skill_experiences.find_by_id(
            SEED_ADAPTIVE_LAB_EXPERIENCE_ID
        )
        assert experience is not None
        experience.status = SkillExperienceStatus.LEARNING
        repositories.skill_experiences.update(experience)
        progress = repositories.competency_progresses.find_by_id(
            SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID
        )
        assert progress is not None
        progress.content_released = True
        repositories.competency_progresses.update(progress)

    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.inngest_broker = _NoopBroker()
    assessor = _FixedCodeRubricAssessorProvider()
    application.dependency_overrides[LearningPipe.get_code_rubric_assessor_provider] = (
        lambda: assessor
    )
    application.state.test_code_rubric_assessor_provider = assessor
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestPreviewActivityQuestionFeedbackController:
    def test_returns_fixed_preliminary_feedback_without_persisting_learning_state(
        self,
        client: TestClient,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum_database.transaction() as repositories:
            repositories.activities.add_many([_mixed_activity()])

        headers = {'Authorization': 'Bearer test-access-token'}
        activity = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(),
                headers=headers,
            ),
        )

        assert activity.status_code == 200, activity.json()
        body = cast('dict[str, object]', activity.json())
        revision = cast('str', body['activity_revision'])

        counts_before = _learning_write_counts(postgres_database)
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{_activity_path()}/questions/{_QUESTION_KEY}/preliminary-evaluations',
                headers=headers,
                json={
                    'activity_revision': revision,
                    'answer': {
                        'kind': 'javascript_stdin',
                        'question_key': _QUESTION_KEY,
                        'files': [
                            {
                                'path': 'src/main.js',
                                'content': "process.stdin.on('data', chunk => console.log(chunk.toString().trim()))",
                            }
                        ],
                    },
                },
            ),
        )

        assert response.status_code == 200, response.json()
        result = response.json()

        assert result['status'] == 'conclusive'
        assert result['score'] == '75'
        assert result['criteria'] == [
            {
                'key': 'correctness',
                'weight_percentage': 100,
                'level': 75,
                'comment_id': 'comment-75',
                'comment': 'Fixed comment 75',
            }
        ]
        assert result['submitted_files'] == [
            {
                'path': 'src/helper.js',
                'content': 'export const helper = 1',
            },
            {
                'path': 'src/main.js',
                'content': "process.stdin.on('data', chunk => console.log(chunk.toString().trim()))",
            },
        ]
        assert 'attempt_id' not in result
        assert application.state.test_code_rubric_assessor_provider.requests[
            0
        ].project_files == (
            (
                'src/helper.js',
                'export const helper = 1',
            ),
            (
                'src/main.js',
                "process.stdin.on('data', chunk => console.log(chunk.toString().trim()))",
            ),
        )
        assert _learning_write_counts(postgres_database) == counts_before


def _activity_path() -> str:
    return (
        f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
        f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
        f'/activities/{_ACTIVITY_ID}'
    )


def _learning_write_counts(postgres_database: PostgresDatabase) -> tuple[int, int, int]:
    with postgres_database.engine.connect() as connection:
        return (
            connection.scalar(select(func.count()).select_from(ActivityAttemptModel))
            or 0,
            connection.scalar(select(func.count()).select_from(ActivityEvaluationModel))
            or 0,
            connection.scalar(select(func.count()).select_from(EventModel)) or 0,
        )


def _mixed_activity() -> Activity:
    questions = tuple(
        SingleChoiceQuestion(
            key=f'q{index}',
            prompt='Escolha',
            options=(ChoiceOption(key='a', text='A', is_correct=True),),
            correct_explanation='Certo',
            incorrect_explanation='Errado',
        )
        for index in (1, 2)
    )
    code = JavascriptStdinQuestion(
        key=_QUESTION_KEY,
        prompt='Leia stdin',
        initial_files=(
            JavascriptInitialFile(
                path='src/main.js', content='console.log(1)', editable=True
            ),
            JavascriptInitialFile(
                path='src/helper.js', content='export const helper = 1', editable=False
            ),
        ),
        entrypoint='src/main.js',
        fixed_dependencies=(),
        permitted_commands=(),
        concept_criteria=(),
    )
    criterion = CodeRubricCriterion(
        key='correctness',
        name='Correção',
        description='Saída',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(
                id=f'comment-{level}', level=level, text=f'Fixed comment {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(id='unknown', text='Inconclusivo'),
    )
    return Activity.create(
        id=_ACTIVITY_ID,
        competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Atividade mista',
        objective='Aprender',
        questions=(*questions, code),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                CodeRubricEvaluationPart(
                    question_key=_QUESTION_KEY,
                    weight_percentage=40,
                    criteria=(criterion,),
                ),
            )
        ),
    )
