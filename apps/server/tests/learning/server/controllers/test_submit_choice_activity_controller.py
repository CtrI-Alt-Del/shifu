from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

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
from shifu.learning.core.domain.structures import CodeAnswer
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import ActivityAttemptModel
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ACTIVITY_REPETITION_EASY_ID,
    SEED_COMPETENCY_REPETITION_ID,
    SEED_GOAL_ID,
    SEED_SKILL_LOGIC_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response


_SUBMISSION_KEY = '75e29c3d-8bc2-4e4d-9103-cc747a170012'


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

    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.inngest_broker = _NoopBroker()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestSubmitChoiceActivityController:
    def test_creates_attempt_and_same_key_replay_returns_the_same_attempt(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        first = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_body(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        attempt_id = cast('str', first.json()['attempt_id'])
        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            assert evaluation is not None
            evaluation.complete(Decimal('100'), datetime.now(UTC), ())
            repositories.activity_evaluations.update(evaluation)
        replay = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_body(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        changed_answer = _body()
        changed_answers = cast('list[dict[str, object]]', changed_answer['answers'])
        changed_answers[0]['selected_option_keys'] = ['incorrect']
        key_mismatch = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=changed_answer,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert first.status_code == 201, first.json()
        assert first.json()['status'] == 'pending'
        assert first.json()['result_url'].endswith(
            f'/attempts/{first.json()["attempt_id"]}'
        )
        assert replay.status_code == 200
        assert replay.json() == first.json()
        assert key_mismatch.status_code == 409
        assert key_mismatch.json()['code'] == 'conflict'
        with postgres_database.engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(ActivityAttemptModel)
                    .where(ActivityAttemptModel.submission_key == _SUBMISSION_KEY)
                )
                == 1
            )

    def test_rejects_semantically_invalid_answers_and_malformed_body(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        invalid_answer = _body()
        invalid_answers = cast('list[dict[str, object]]', invalid_answer['answers'])
        invalid_answers[0]['selected_option_keys'] = ['not-an-option']
        invalid = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=invalid_answer,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        malformed = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json={'submission_key': 'not-a-uuid', 'answers': []},
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert invalid.status_code == 400
        assert invalid.json()['code'] == 'validation_error'
        assert malformed.status_code == 422
        with postgres_database.engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count()).select_from(ActivityAttemptModel)
                )
                == 3
            )

    def test_mixed_submission_persists_the_saved_snapshot_and_code_files(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        activity = _mixed_activity()
        curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum_database.transaction() as repositories:
            repositories.activities.add_many([activity])

        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(activity.id),
                headers=headers,
            ),
        )
        assert detail.status_code == 200, detail.json()
        revision = cast('str', detail.json()['activity_revision'])
        body: dict[str, object] = {
            'submission_key': '7c3c84ce-7185-43bc-8b75-c9b250000091',
            'activity_revision': revision,
            'answers': [
                {
                    'kind': 'single_choice',
                    'question_key': 'q1',
                    'selected_option_keys': ['a'],
                },
                {
                    'kind': 'single_choice',
                    'question_key': 'q2',
                    'selected_option_keys': ['a'],
                },
                {
                    'kind': 'javascript_stdin',
                    'question_key': 'q3',
                    'files': [{'path': 'src/main.js', 'content': 'console.log(7)'}],
                },
            ],
        }

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(activity.id),
                json=body,
                headers=headers,
            ),
        )

        assert response.status_code == 201, response.json()
        attempt_id = cast('str', response.json()['attempt_id'])
        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
        assert attempt is not None
        assert attempt.grading_snapshot is not None
        assert attempt.grading_snapshot.id == activity.id
        code_answer = attempt.answers[2]
        assert isinstance(code_answer, CodeAnswer)
        assert code_answer.files[0].content == 'console.log(7)'
        assert evaluation is not None
        assert evaluation.status.value == 'pending'
        assert evaluation.run_id is not None

        replay = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(activity.id),
                json=body,
                headers=headers,
            ),
        )
        assert replay.status_code == 200
        assert replay.json()['attempt_id'] == attempt_id


def _attempts_path(
    activity_id: str = SEED_ACTIVITY_REPETITION_EASY_ID,
) -> str:
    return (
        f'/learning/goals/{SEED_GOAL_ID}/skills/{SEED_SKILL_LOGIC_ID}'
        f'/competencies/{SEED_COMPETENCY_REPETITION_ID}'
        f'/activities/{activity_id}/attempts'
    )


def _body() -> dict[str, object]:
    return {
        'submission_key': str(UUID(_SUBMISSION_KEY)),
        'answers': [
            {
                'question_key': question_key,
                'selected_option_keys': ['correct'],
            }
            for question_key in ('question-one', 'question-two', 'question-three')
        ],
    }


def _activity_path(activity_id: str) -> str:
    return _attempts_path(activity_id).removesuffix('/attempts')


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
        key='q3',
        prompt='Leia stdin',
        initial_files=(
            JavascriptInitialFile(
                path='src/main.js', content='console.log(1)', editable=True
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
        id='01SHF000000000000000000091',
        competency_id=SEED_COMPETENCY_REPETITION_ID,
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
                    question_key='q3', weight_percentage=40, criteria=(criterion,)
                ),
            )
        ),
    )
