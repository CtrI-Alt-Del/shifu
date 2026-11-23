from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest
from fastapi import Request
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
    ChoiceConceptCriterion,
    OrderingQuestion,
    OrderingStep,
    SingleChoiceQuestion,
    TranslationInconclusiveComment,
    TranslationQuestion,
    TranslationRubricComment,
    TranslationRubricCriterion,
    TranslationRubricEvaluationPart,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.core.domain.structures import (
    CodeAnswer,
    OrderingAnswer,
    FillBlanksAnswer,
    FillBlanksPlacement,
    PairMatchingAnswer,
    PairMatchingSelection,
    SingleChoiceAnswer,
    TranslationAnswer,
)
from shifu.learning.core.domain.enums import (
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.identity.database.sqlalchemy.identity_database import (
    SqlalchemyIdentityDatabase,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import ActivityAttemptModel
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import (
    AuthenticatedUser,
    CurriculumReactQuestionSnapshot,
)
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,
    SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    build_development_seed,
)
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe
from tests.fixtures.fill_blanks_activity_fixture import (
    CORRECT_PAIRS,
    PARTIAL_PAIRS,
    FillBlanksActivityFixture,
)
from tests.fixtures.image_choice_activity_fixture import ImageChoiceActivityFixture
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.learning.rest.controllers.pair_matching_controller_fixture import (
    PairMatchingControllerFixture,
)
from tests.fixtures.react_fastify_activity_fixture import ReactFastifyActivityFixture
from tests.fixtures.redis_fixture import RedisFixture
from tests.fixtures.react_activity_fixture import (
    ReactControllerFixture,
)

if TYPE_CHECKING:
    from httpx import Response


_SUBMISSION_KEY = '75e29c3d-8bc2-4e4d-9103-cc747a170012'
_ACTIVITY_ID = SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS[3]


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
            session_id='test-account-activity-session',
            token_access_version=1,
            account_access_version=1,
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
    learning_started_at = datetime(2026, 1, 1, tzinfo=UTC)
    for experience in seed.skill_experiences:
        if experience.status is not SkillExperienceStatus.NOT_STARTED:
            continue
        experience.start_diagnosis(learning_started_at)
        experience.start_learning(learning_started_at)
    for progress in seed.competency_progresses:
        progress.content_released = True
        progress.initial_progress = Decimal('55')
        progress.current_progress = Decimal('55')
        progress.status = CompetencyProgressStatus.DEVELOPING
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

    with SqlalchemyIdentityDatabase(
        engine=postgres_database.engine
    ).transaction() as repositories:
        for account in seed.accounts:
            repositories.accounts.add(account)

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
    def test_ordering_submission_consumes_verified_passage_and_replays_immutably(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        activity = _ordering_activity()
        with SqlalchemyCurriculumDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            repositories.activities.add_many([activity])

        headers = {'Authorization': 'Bearer test-access-token'}
        path = _activity_path(activity.id)
        detail = cast(
            'Response',
            client.get(path, headers=headers),  # pyright: ignore[reportUnknownMemberType]
        )

        assert detail.status_code == 200, detail.json()
        revision = cast('str', detail.json()['activity_revision'])
        passage_key = 'bf180869-1f71-42da-b621-363af4fd0001'
        accepted_order = ['first', 'second', 'third']
        for question_key in ('q1', 'q2', 'q3'):
            preview = cast(
                'Response',
                client.post(
                    f'{path}/questions/{question_key}/preliminary-evaluations',
                    headers=headers,
                    json={
                        'activity_revision': revision,
                        'passage_key': passage_key,
                        'answer': {
                            'kind': 'ordering',
                            'question_key': question_key,
                            'ordered_step_keys': accepted_order,
                        },
                    },
                ),  # pyright: ignore[reportUnknownMemberType]
            )
            assert preview.status_code == 200, preview.json()
            assert preview.json()['score'] == '100'

        body: dict[str, object] = {
            'submission_key': '3498265c-cd47-4ef2-a9f7-8d131e7bc001',
            'passage_key': passage_key,
            'activity_revision': revision,
            'answers': [
                {
                    'kind': 'ordering',
                    'question_key': question_key,
                    'ordered_step_keys': accepted_order,
                }
                for question_key in ('q1', 'q2', 'q3')
            ],
        }

        created = cast(
            'Response',
            client.post(_attempts_path(activity.id), headers=headers, json=body),  # pyright: ignore[reportUnknownMemberType]
        )
        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])

        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            experience = repositories.skill_experiences.find_by_id(
                SEED_ADAPTIVE_LAB_EXPERIENCE_ID
            )
            assert experience is not None
            passage = repositories.ordering_passages.find_by_key(
                experience.id, activity.id, passage_key
            )
            active_passage = repositories.ordering_passages.find_active(
                experience.id, activity.id
            )

        assert attempt is not None
        assert attempt.grading_snapshot is not None
        assert [answer.question_key for answer in attempt.answers] == [
            'q1',
            'q2',
            'q3',
        ]
        ordering_answers = tuple(
            answer for answer in attempt.answers if isinstance(answer, OrderingAnswer)
        )
        assert len(ordering_answers) == len(attempt.answers) == 3
        assert all(
            answer.ordered_step_keys == tuple(accepted_order)
            for answer in ordering_answers
        )
        assert passage is not None
        assert passage.status == 'consumed'
        assert active_passage is None

        replay = cast(
            'Response',
            client.post(_attempts_path(activity.id), headers=headers, json=body),  # pyright: ignore[reportUnknownMemberType]
        )
        assert replay.status_code == 200, replay.json()
        assert replay.json() == created.json()

        late_preview = cast(
            'Response',
            client.post(
                f'{path}/questions/q1/preliminary-evaluations',
                headers=headers,
                json={
                    'activity_revision': revision,
                    'passage_key': passage_key,
                    'answer': {
                        'kind': 'ordering',
                        'question_key': 'q1',
                        'ordered_step_keys': accepted_order,
                    },
                },
            ),  # pyright: ignore[reportUnknownMemberType]
        )
        assert late_preview.status_code == 409

    @pytest.mark.parametrize('with_policy', [True, False])
    def test_integrated_submission_is_immutable_replayed_and_sent_to_learning(
        self,
        client: TestClient,
        application: FastAPI,
        postgres_database: PostgresDatabase,
        with_policy: bool,
    ) -> None:
        with SqlalchemyCurriculumDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            repositories.activities.add_many(
                [ReactFastifyActivityFixture.activity(with_policy=with_policy)]
            )
        headers = {'Authorization': 'Bearer test-access-token'}
        path = ReactFastifyActivityFixture.activity_path()
        detail = client.get(path, headers=headers)
        assert detail.status_code == 200, detail.text
        body = ReactFastifyActivityFixture.submission(
            detail.json()['activity_revision'], with_additional=with_policy
        )
        created = client.post(path + '/attempts', headers=headers, json=body)
        assert created.status_code == 201, created.text
        attempt_id = created.json()['attempt_id']
        with SqlalchemyLearningDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
        assert attempt is not None and attempt.grading_snapshot is not None
        question = attempt.grading_snapshot.questions[2]
        assert question.kind == 'react_fastify'
        answer = attempt.answers[2]
        assert isinstance(answer, CodeAnswer)
        assert answer.kind == 'react_fastify'
        assert {item.path: item.content for item in answer.files}[
            'api.js'
        ] == ReactFastifyActivityFixture.API_SOURCE
        with SqlalchemyLearningDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            events = repositories.events.find_unrouted(now=datetime.now(UTC), limit=100)
        event = next(
            item for item in events if item.payload.get('attempt_id') == attempt_id
        )
        assert (
            application.state.learning_workflows_registry.destination_for_event(event)
            == 'agentos:learning'
        )
        assert set(event.payload) >= {'attempt_id', 'run_id'}
        assert 'files' not in event.payload
        counts = ReactControllerFixture.write_counts(postgres_database)
        replay = client.post(path + '/attempts', headers=headers, json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json() == created.json()
        assert ReactControllerFixture.write_counts(postgres_database) == counts
        history = client.get(path + '/attempts/' + attempt_id, headers=headers)
        assert history.status_code == 200, history.text
        integrated = next(
            item
            for item in history.json()['questions']
            if item['kind'] == 'react_fastify'
        )
        assert {
            item['path']: item['content'] for item in integrated['submitted_files']
        }['api.js'] == ReactFastifyActivityFixture.API_SOURCE

    @pytest.mark.parametrize(
        'answer',
        (
            {'kind': 'react', 'question_key': 'q3'},
            {
                'kind': 'react',
                'question_key': 'q3',
                'files': [],
                'selected_option_keys': ['a'],
            },
            {'kind': 'single_choice', 'question_key': 'q1'},
            {
                'kind': 'single_choice',
                'question_key': 'q1',
                'files': [],
                'selected_option_keys': ['a'],
            },
            {'kind': 'ordering', 'question_key': 'q1'},
            {
                'kind': 'ordering',
                'question_key': 'q1',
                'ordered_step_keys': ['a', 'b', 'c'],
                'text': 'Texto que pertence ao formato tradução.',
            },
            {
                'kind': 'translation',
                'question_key': 'q1',
                'text': 'Uma tradução.',
                'ordered_step_keys': ['a', 'b', 'c'],
            },
        ),
        ids=(
            'code-without-files',
            'mixed-code-shape',
            'choice-without-options',
            'mixed-choice-shape',
            'ordering-without-steps',
            'ordering-with-translation-text',
            'translation-with-ordering-steps',
        ),
    )
    def test_should_reject_malformed_answer_shape_before_persistence(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        answer: dict[str, object],
    ) -> None:
        before = ReactControllerFixture.write_counts(postgres_database)

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                headers={'Authorization': 'Bearer test-access-token'},
                json={
                    'submission_key': 'e9aa7b85-c95b-4319-b98e-5ca293c09f61',
                    'answers': [answer],
                },
            ),
        )

        assert response.status_code == 422, response.json()
        assert ReactControllerFixture.write_counts(postgres_database) == before

    @pytest.mark.parametrize('with_policy', [True, False])
    def test_react_submission_round_trips_files_policy_and_same_key_replay(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
        with_policy: bool,
    ) -> None:
        def no_request_id(_request: Request) -> None:
            return None

        monkeypatch.setattr(
            TelemetryPipe,
            'get_request_id',
            staticmethod(no_request_id),
        )
        curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum.transaction() as repositories:
            repositories.activities.add_many(
                [ReactControllerFixture.activity(with_policy=with_policy)]
            )
        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ReactControllerFixture.activity_path(), headers=headers
            ),
        )
        assert detail.status_code == 200, detail.json()
        revision = cast('str', detail.json()['activity_revision'])
        body = ReactControllerFixture.submission(revision)
        answers = cast('list[dict[str, object]]', body['answers'])
        if not with_policy:
            answers[2]['files'] = ReactControllerFixture.answer_files()[:1]
        before = ReactControllerFixture.write_counts(postgres_database)

        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                json=body,
                headers=headers,
            ),
        )

        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        assert created.json()['status'] == 'pending'
        assert created.json()['result_url'].endswith(f'/attempts/{attempt_id}')
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
        assert attempt is not None
        snapshot = attempt.grading_snapshot
        assert snapshot is not None
        assert snapshot.revision == revision
        question = snapshot.questions[2]
        assert isinstance(question, CurriculumReactQuestionSnapshot)
        assert question.kind == 'react'
        assert question.prompt == ReactControllerFixture.PROMPT
        assert (
            question.initial_files[0].content == ReactControllerFixture.INITIAL_SOURCE
        )
        assert question.initial_files[1].content == ReactControllerFixture.FIXED_HTML
        assert (question.additional_file_policy is not None) is with_policy
        if question.additional_file_policy is not None:
            assert question.additional_file_policy.allowed_directories == (
                'src/components',
            )
            assert question.additional_file_policy.allowed_extensions == ('.jsx', '.js')
            assert question.additional_file_policy.max_files == 2
        answer = attempt.answers[2]
        assert isinstance(answer, CodeAnswer)
        assert answer.kind == 'react'
        assert [
            {'path': file.path, 'content': file.content} for file in answer.files
        ] == (
            ReactControllerFixture.answer_files()
            if with_policy
            else ReactControllerFixture.answer_files()[:1]
        )
        assert evaluation is not None and evaluation.status.value == 'pending'
        assert evaluation.run_id is not None
        after_created = ReactControllerFixture.write_counts(postgres_database)
        assert after_created == (before[0] + 1, before[1] + 1, before[2], before[3] + 1)

        replay = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                json=body,
                headers=headers,
            ),
        )

        assert replay.status_code == 200, replay.json()
        assert replay.json() == created.json()
        assert ReactControllerFixture.write_counts(postgres_database) == after_created

    def test_react_submit_uses_configured_assessment_size_limit(
        self,
        client: TestClient,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum.transaction() as repositories:
            repositories.activities.add_many([ReactControllerFixture.activity()])
        application.dependency_overrides[
            LearningPipe.get_max_code_assessment_input_bytes
        ] = lambda: 512 * 1024
        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ReactControllerFixture.activity_path(), headers=headers
            ),
        )
        assert detail.status_code == 200, detail.json()
        body = ReactControllerFixture.submission(
            cast('str', detail.json()['activity_revision'])
        )
        answers = cast('list[dict[str, object]]', body['answers'])
        large_source = 'x' * (300 * 1024)
        answers[2]['files'] = [{'path': 'src/App.jsx', 'content': large_source}]

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                json=body,
                headers=headers,
            ),
        )

        assert response.status_code == 201, response.json()
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(
                cast('str', response.json()['attempt_id'])
            )
        assert attempt is not None
        answer = attempt.answers[2]
        assert isinstance(answer, CodeAnswer)
        assert answer.files[0].content == large_source

    @pytest.mark.parametrize('with_policy', [True, False])
    def test_react_submit_rejects_forbidden_extra_files_without_persistence(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        with_policy: bool,
    ) -> None:
        curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum.transaction() as repositories:
            repositories.activities.add_many(
                [ReactControllerFixture.activity(with_policy=with_policy)]
            )
        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ReactControllerFixture.activity_path(), headers=headers
            ),
        )
        assert detail.status_code == 200, detail.json()
        body = ReactControllerFixture.submission(
            cast('str', detail.json()['activity_revision'])
        )
        answers = cast('list[dict[str, object]]', body['answers'])
        files = cast('list[dict[str, str]]', answers[2]['files'])
        if with_policy:
            files[1]['path'] = 'src/unauthorized.jsx'
        before = ReactControllerFixture.write_counts(postgres_database)

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                json=body,
                headers=headers,
            ),
        )

        assert response.status_code == 400, response.json()
        assert response.json()['code'] == 'validation_error'
        assert ReactControllerFixture.write_counts(postgres_database) == before

    def test_creates_attempt_and_same_key_replay_returns_the_same_attempt(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        first = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_body(client),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert first.status_code == 201, first.json()
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
                json=_body(client),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        changed_answer = _body(client)
        changed_answers = cast('list[dict[str, object]]', changed_answer['answers'])
        changed_answers[0]['selected_option_keys'] = ['b']
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
        invalid_answer = _body(client)
        invalid_answers = cast('list[dict[str, object]]', invalid_answer['answers'])
        invalid_answers[0]['selected_option_keys'] = ['not-an-option']
        with postgres_database.engine.connect() as connection:
            attempts_before = connection.scalar(
                select(func.count()).select_from(ActivityAttemptModel)
            )
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
                == attempts_before
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

    def _fill_revision(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> str:
        with SqlalchemyCurriculumDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            repositories.activities.add_many([FillBlanksActivityFixture.activity()])
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                FillBlanksActivityFixture.activity_path(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        assert detail.status_code == 200, detail.json()
        return cast('str', detail.json()['activity_revision'])

    def _fill_submit(self, client: TestClient, body: dict[str, object]) -> 'Response':
        return cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                FillBlanksActivityFixture.activity_path() + '/attempts',
                json=body,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

    def test_fill_blanks_submission_persists_normalized_placements_and_replays(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        revision = self._fill_revision(client, postgres_database)
        before = FillBlanksActivityFixture.write_counts(postgres_database)
        reordered = tuple(reversed(CORRECT_PAIRS))
        body = FillBlanksActivityFixture.submission(revision, *reordered)

        created = self._fill_submit(client, body)

        assert created.status_code == 201, created.json()
        assert created.json()['status'] == 'pending'
        attempt_id = cast('str', created.json()['attempt_id'])
        attempts, evaluations, observations, events = (
            FillBlanksActivityFixture.write_counts(postgres_database)
        )
        assert (
            attempts - before[0],
            evaluations - before[1],
            observations - before[2],
            events - before[3],
        ) == (1, 1, 0, 1)
        with SqlalchemyLearningDatabase(postgres_database.engine).transaction() as (
            repositories
        ):
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
        assert attempt is not None and attempt.grading_snapshot is not None
        assert attempt.grading_snapshot.questions[0].kind == 'fill_blanks'
        assert attempt.grading_snapshot.revision == revision
        assert attempt.answers[0] == FillBlanksAnswer(
            question_key='fill-1',
            placements=tuple(
                FillBlanksPlacement(blank_key=blank, word_key=word)
                for blank, word in CORRECT_PAIRS
            ),
        )
        assert evaluation is not None
        assert evaluation.status.value == 'pending'

        replay = self._fill_submit(client, body)
        different = self._fill_submit(
            client, FillBlanksActivityFixture.submission(revision, *PARTIAL_PAIRS)
        )

        assert replay.status_code == 200, replay.json()
        assert replay.json()['attempt_id'] == attempt_id
        assert different.status_code == 409, different.json()
        assert FillBlanksActivityFixture.write_counts(postgres_database) == (
            attempts,
            evaluations,
            observations,
            events,
        )

    def test_fill_blanks_submission_accepts_a_complete_but_wrong_fill(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        revision = self._fill_revision(client, postgres_database)

        created = self._fill_submit(
            client, FillBlanksActivityFixture.submission(revision, *PARTIAL_PAIRS)
        )

        assert created.status_code == 201, created.json()

    @pytest.mark.parametrize(
        ('pairs', 'expected_status'),
        (
            ((('b1', 'w1'), ('b2', 'w3')), 400),
            ((('b1', 'w1'), ('b2', 'w1'), ('b3', 'w4')), 400),
            ((('b1', 'w1'), ('b2', 'missing'), ('b3', 'w4')), 400),
            ((('b1', 'w1'), ('b2', 'w3'), ('unknown', 'w4')), 400),
            ((), 400),
        ),
        ids=(
            'incomplete',
            'repeated-occurrence',
            'unknown-occurrence',
            'unknown-blank',
            'empty',
        ),
    )
    def test_fill_blanks_submission_rejects_an_invalid_fill_without_persistence(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        pairs: tuple[tuple[str, str], ...],
        expected_status: int,
    ) -> None:
        revision = self._fill_revision(client, postgres_database)
        before = FillBlanksActivityFixture.write_counts(postgres_database)

        response = self._fill_submit(
            client, FillBlanksActivityFixture.submission(revision, *pairs)
        )

        assert response.status_code == expected_status, response.json()
        assert FillBlanksActivityFixture.write_counts(postgres_database) == before

    @pytest.mark.parametrize(
        'mutation',
        ('placements-on-choice', 'fill-with-options', 'fill-without-placements'),
    )
    def test_fill_blanks_submission_rejects_malformed_answer_shapes(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        mutation: str,
    ) -> None:
        revision = self._fill_revision(client, postgres_database)
        before = FillBlanksActivityFixture.write_counts(postgres_database)
        body = FillBlanksActivityFixture.submission(revision, *CORRECT_PAIRS)
        answers = cast('list[dict[str, object]]', body['answers'])
        if mutation == 'placements-on-choice':
            answers[1]['placements'] = []
        elif mutation == 'fill-with-options':
            answers[0]['selected_option_keys'] = ['a']
        else:
            del answers[0]['placements']

        response = self._fill_submit(client, body)

        assert response.status_code == 422, response.json()
        assert FillBlanksActivityFixture.write_counts(postgres_database) == before

    def test_fill_blanks_submission_rejects_a_stale_revision_and_a_pending_evaluation(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        revision = self._fill_revision(client, postgres_database)
        before = FillBlanksActivityFixture.write_counts(postgres_database)

        stale = self._fill_submit(
            client,
            FillBlanksActivityFixture.submission('stale-revision', *CORRECT_PAIRS),
        )
        assert stale.status_code == 409, stale.json()
        assert FillBlanksActivityFixture.write_counts(postgres_database) == before

        first = self._fill_submit(
            client, FillBlanksActivityFixture.submission(revision, *CORRECT_PAIRS)
        )
        assert first.status_code == 201, first.json()
        pending = FillBlanksActivityFixture.write_counts(postgres_database)
        second = self._fill_submit(
            client,
            FillBlanksActivityFixture.submission(
                revision,
                *CORRECT_PAIRS,
                submission_key='11111111-1111-4111-8111-111111111111',
            ),
        )

        assert second.status_code == 409, second.json()
        assert FillBlanksActivityFixture.write_counts(postgres_database) == pending

    def test_mixed_translation_submission_persists_the_saved_snapshot_and_text(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        activity = _mixed_translation_activity()
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
            'submission_key': '7c3c84ce-7185-43bc-8b75-c9b250000092',
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
                    'kind': 'translation',
                    'question_key': 'q3',
                    'text': 'Good morning',
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
        translation_answer = attempt.answers[2]

        assert isinstance(translation_answer, TranslationAnswer)
        assert translation_answer.text == 'Good morning'
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

        conflicting_body = {
            **body,
            'answers': [
                *cast('list[object]', body['answers'])[:2],
                {'kind': 'translation', 'question_key': 'q3', 'text': 'Good evening'},
            ],
        }
        conflicting_replay = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(activity.id),
                json=conflicting_body,
                headers=headers,
            ),
        )

        assert conflicting_replay.status_code == 409
        assert conflicting_replay.json()['code'] == 'conflict'

    def _persist_pair_activity(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> str:
        curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum_database.transaction() as repositories:
            repositories.activities.add_many([PairMatchingControllerFixture.activity()])
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                PairMatchingControllerFixture.activity_path(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        assert detail.status_code == 200, detail.json()
        return cast('str', detail.json()['activity_revision'])

    def test_pair_submission_persists_the_saved_pairs_and_replays_idempotently(
        self,
        client: TestClient,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        revision = self._persist_pair_activity(client, postgres_database)
        headers = {'Authorization': 'Bearer test-access-token'}
        body = PairMatchingControllerFixture.submission(revision, 1, 0, 2)
        before = ReactControllerFixture.write_counts(postgres_database)

        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                PairMatchingControllerFixture.attempts_path(),
                json=body,
                headers=headers,
            ),
        )

        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        after = ReactControllerFixture.write_counts(postgres_database)
        # One attempt, one pending evaluation and one outbox event; no Concept rows.
        assert tuple(b - a for a, b in zip(before, after, strict=True)) == (1, 1, 0, 1)
        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
        assert attempt is not None
        assert attempt.grading_snapshot is not None
        assert attempt.grading_snapshot.id == PairMatchingControllerFixture.ACTIVITY_ID
        saved = attempt.answers[2]
        assert isinstance(saved, PairMatchingAnswer)
        assert saved.pairs == tuple(
            PairMatchingSelection(
                word_key=item['word_key'], translation_key=item['translation_key']
            )
            for item in PairMatchingControllerFixture.pairs(1, 0, 2)
        )
        assert evaluation is not None
        assert evaluation.status.value == 'pending'
        with learning_database.transaction() as repositories:
            events = repositories.events.find_unrouted(now=datetime.now(UTC), limit=100)
        event = next(
            item for item in events if item.payload.get('attempt_id') == attempt_id
        )
        # No AI-graded question: the evaluation stays on the deterministic path.
        assert (
            application.state.learning_workflows_registry.destination_for_event(event)
            == 'inngest'
        )

        replay = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                PairMatchingControllerFixture.attempts_path(),
                json=body,
                headers=headers,
            ),
        )

        assert replay.status_code == 200, replay.json()
        assert replay.json()['attempt_id'] == attempt_id
        assert ReactControllerFixture.write_counts(postgres_database) == after

        conflicting = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                PairMatchingControllerFixture.attempts_path(),
                json=PairMatchingControllerFixture.submission(revision, 0, 1, 2),
                headers=headers,
            ),
        )

        assert conflicting.status_code == 409, conflicting.json()
        assert conflicting.json()['code'] == 'conflict'
        assert ReactControllerFixture.write_counts(postgres_database) == after

    @pytest.mark.parametrize(
        ('pairs', 'status_code'),
        (
            ([], 422),
            (PairMatchingControllerFixture.pairs(0, 1), 400),
            (
                [
                    {'word_key': 'word-0', 'translation_key': 'translation-0'},
                    {'word_key': 'word-0', 'translation_key': 'translation-1'},
                    {'word_key': 'word-2', 'translation_key': 'translation-2'},
                ],
                400,
            ),
            (
                [
                    {'word_key': 'word-0', 'translation_key': 'translation-0'},
                    {'word_key': 'word-1', 'translation_key': 'translation-1'},
                    {'word_key': 'word-2', 'translation_key': 'translation-9'},
                ],
                400,
            ),
        ),
        ids=('empty', 'incomplete', 'repeated-word', 'unknown-translation'),
    )
    def test_pair_submission_rejects_invalid_pairs_without_persisting(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        pairs: list[dict[str, str]],
        status_code: int,
    ) -> None:
        revision = self._persist_pair_activity(client, postgres_database)
        body = PairMatchingControllerFixture.submission(revision)
        answers = cast('list[dict[str, object]]', body['answers'])
        answers[2] = {**answers[2], 'pairs': pairs}
        before = ReactControllerFixture.write_counts(postgres_database)

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                PairMatchingControllerFixture.attempts_path(),
                json=body,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == status_code, response.json()
        assert ReactControllerFixture.write_counts(postgres_database) == before

    def test_pair_submission_rejects_a_stale_activity_revision(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        self._persist_pair_activity(client, postgres_database)
        before = ReactControllerFixture.write_counts(postgres_database)

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                PairMatchingControllerFixture.attempts_path(),
                json=PairMatchingControllerFixture.submission('stale-revision'),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 409, response.json()
        assert ReactControllerFixture.write_counts(postgres_database) == before

    def _image_revision(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> str:
        with SqlalchemyCurriculumDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            repositories.activities.add_many([ImageChoiceActivityFixture.activity()])
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ImageChoiceActivityFixture.activity_path(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        assert detail.status_code == 200, detail.json()
        return cast('str', detail.json()['activity_revision'])

    def _image_submit(self, client: TestClient, body: dict[str, object]) -> 'Response':
        return cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                ImageChoiceActivityFixture.attempts_path(),
                json=body,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

    def test_image_choice_submission_persists_one_single_answer_and_replays(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        revision = self._image_revision(client, postgres_database)
        before = ImageChoiceActivityFixture.write_counts(postgres_database)
        chosen = ImageChoiceActivityFixture.OPTION_KEYS[0]
        body = ImageChoiceActivityFixture.submission(revision, chosen)

        created = self._image_submit(client, body)

        assert created.status_code == 201, created.json()
        assert created.json()['status'] == 'pending'
        attempt_id = cast('str', created.json()['attempt_id'])
        attempts, evaluations, observations, events = (
            ImageChoiceActivityFixture.write_counts(postgres_database)
        )
        assert (
            attempts - before[0],
            evaluations - before[1],
            observations - before[2],
            events - before[3],
        ) == (1, 1, 0, 1)
        # A new session reads the stored attempt through the attempt mapper.
        with SqlalchemyLearningDatabase(postgres_database.engine).transaction() as (
            repositories
        ):
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
        assert attempt is not None and attempt.grading_snapshot is not None
        assert attempt.grading_snapshot.questions[1].kind == 'image_choice'
        assert attempt.grading_snapshot.revision == revision
        assert attempt.answers[1] == SingleChoiceAnswer(
            question_key='image-1', selected_option_key=chosen
        )
        assert evaluation is not None
        assert evaluation.status.value == 'pending'

        replay = self._image_submit(client, body)
        different = self._image_submit(
            client,
            ImageChoiceActivityFixture.submission(
                revision, ImageChoiceActivityFixture.CORRECT_OPTION_KEY
            ),
        )

        assert replay.status_code == 200, replay.json()
        assert replay.json()['attempt_id'] == attempt_id
        assert different.status_code == 409, different.json()
        assert ImageChoiceActivityFixture.write_counts(postgres_database) == (
            attempts,
            evaluations,
            observations,
            events,
        )

    @pytest.mark.parametrize(
        ('option_keys', 'expected_status'),
        (
            ((), 422),
            (ImageChoiceActivityFixture.OPTION_KEYS[:2], 422),
            (('opt-ffffffffffff',), 400),
        ),
        ids=('no-key', 'two-keys', 'unknown-key'),
    )
    def test_image_choice_submission_rejects_invalid_keys_without_persistence(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        option_keys: tuple[str, ...],
        expected_status: int,
    ) -> None:
        revision = self._image_revision(client, postgres_database)
        before = ImageChoiceActivityFixture.write_counts(postgres_database)

        response = self._image_submit(
            client, ImageChoiceActivityFixture.submission(revision, *option_keys)
        )

        assert response.status_code == expected_status, response.json()
        assert ImageChoiceActivityFixture.write_counts(postgres_database) == before

    def test_image_choice_next_to_a_code_question_is_sent_to_the_learning_workflow(
        self,
        client: TestClient,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        with SqlalchemyCurriculumDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            repositories.activities.add_many(
                [ImageChoiceActivityFixture.code_activity()]
            )
        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ImageChoiceActivityFixture.activity_path(), headers=headers
            ),
        )
        assert detail.status_code == 200, detail.json()
        assert [item['kind'] for item in detail.json()['questions']] == [
            'single_choice',
            'image_choice',
            'react',
        ]
        chosen = ImageChoiceActivityFixture.CORRECT_OPTION_KEY
        body = ImageChoiceActivityFixture.submission(
            cast('str', detail.json()['activity_revision']), chosen
        )
        answers = cast('list[dict[str, object]]', body['answers'])
        answers[2] = {
            'kind': 'react',
            'question_key': 'q3',
            'files': [
                {
                    'path': 'src/App.jsx',
                    'content': 'export default function App() { return <h1>Oi</h1> }',
                }
            ],
        }

        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                ImageChoiceActivityFixture.attempts_path(), json=body, headers=headers
            ),
        )

        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        with SqlalchemyLearningDatabase(postgres_database.engine).transaction() as (
            repositories
        ):
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            events = repositories.events.find_unrouted(now=datetime.now(UTC), limit=100)
        assert attempt is not None
        assert attempt.answers[1] == SingleChoiceAnswer(
            question_key='image-1', selected_option_key=chosen
        )
        event = next(
            item for item in events if item.payload.get('attempt_id') == attempt_id
        )
        assert (
            application.state.learning_workflows_registry.destination_for_event(event)
            == 'agentos:learning'
        )

    def test_image_choice_submission_rejects_a_field_of_another_format(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        revision = self._image_revision(client, postgres_database)
        before = ImageChoiceActivityFixture.write_counts(postgres_database)
        body = ImageChoiceActivityFixture.submission(
            revision, ImageChoiceActivityFixture.CORRECT_OPTION_KEY
        )
        answers = cast('list[dict[str, object]]', body['answers'])
        answers[1]['ordered_step_keys'] = ['a']

        response = self._image_submit(client, body)

        assert response.status_code == 422, response.json()
        assert ImageChoiceActivityFixture.write_counts(postgres_database) == before

    def test_image_choice_submission_rejects_a_stale_revision_and_a_pending_evaluation(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        revision = self._image_revision(client, postgres_database)
        before = ImageChoiceActivityFixture.write_counts(postgres_database)
        correct = ImageChoiceActivityFixture.CORRECT_OPTION_KEY

        stale = self._image_submit(
            client, ImageChoiceActivityFixture.submission('stale-revision', correct)
        )
        assert stale.status_code == 409, stale.json()
        assert ImageChoiceActivityFixture.write_counts(postgres_database) == before

        first = self._image_submit(
            client, ImageChoiceActivityFixture.submission(revision, correct)
        )
        assert first.status_code == 201, first.json()
        pending = ImageChoiceActivityFixture.write_counts(postgres_database)
        blocked = self._image_submit(
            client,
            ImageChoiceActivityFixture.submission(
                revision,
                correct,
                submission_key='22222222-2222-4222-8222-222222222222',
            ),
        )

        assert blocked.status_code == 409, blocked.json()
        assert ImageChoiceActivityFixture.write_counts(postgres_database) == pending


def _attempts_path(
    activity_id: str = _ACTIVITY_ID,
) -> str:
    return (
        f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
        f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
        f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
        f'/activities/{activity_id}/attempts'
    )


def _body(client: TestClient) -> dict[str, object]:
    detail = cast(
        'Response',
        client.get(  # pyright: ignore[reportUnknownMemberType]
            _activity_path(_ACTIVITY_ID),
            headers={'Authorization': 'Bearer test-access-token'},
        ),
    )
    assert detail.status_code == 200, detail.json()
    questions = cast('list[dict[str, object]]', detail.json()['questions'])
    answers = [
        {
            'kind': 'single_choice',
            'question_key': question['key'],
            'selected_option_keys': [
                cast('dict[str, str]', cast('list[object]', question['options'])[0])[
                    'key'
                ]
            ],
        }
        for question in questions
    ]
    return {
        'submission_key': str(UUID(_SUBMISSION_KEY)),
        'activity_revision': detail.json()['activity_revision'],
        'answers': answers,
    }


def _activity_path(activity_id: str) -> str:
    return _attempts_path(activity_id).removesuffix('/attempts')


def _ordering_activity() -> Activity:
    questions = tuple(
        OrderingQuestion(
            key=f'q{index}',
            prompt='Organize as etapas.',
            steps=(
                OrderingStep(key='first', text='Preparar os ingredientes.'),
                OrderingStep(key='second', text='Misturar os ingredientes.'),
                OrderingStep(key='third', text='Assar a mistura.'),
            ),
            accepted_orders=(
                ('first', 'second', 'third'),
                ('first', 'third', 'second'),
            ),
            correct_explanation='A ordem correta explica o processo.',
            incorrect_explanation='A ordem precisa ser revista.',
            concept_criteria=(
                ChoiceConceptCriterion(
                    concept_id=SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,
                    criterion='Compreende a sequência.',
                    examples='Prepara antes de misturar.',
                    limits='Não presume etapas ausentes.',
                    correct_score=100,
                    incorrect_score=0,
                ),
            ),
        )
        for index in (1, 2, 3)
    )
    return Activity.create(
        id='01SHF000000000000000000091',
        competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Atividade de ordenação',
        objective='Organizar um processo.',
        questions=questions,
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(question_key='q1', weight_percentage=34),
                CorrectnessEvaluationPart(question_key='q2', weight_percentage=33),
                CorrectnessEvaluationPart(question_key='q3', weight_percentage=33),
            )
        ),
    )


def _mixed_activity() -> Activity:
    questions = tuple(
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
                    question_key='q3', weight_percentage=40, criteria=(criterion,)
                ),
            )
        ),
    )


def _mixed_translation_activity() -> Activity:
    questions = tuple(
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
    translation = TranslationQuestion(
        key='q3',
        prompt='Traduza o texto a seguir.',
        source_language='pt-BR',
        target_language='en-US',
        source_text='Bom dia',
        reference_translations=('Good morning',),
        concept_criteria=(),
    )

    def rubric_criterion(key: str, weight: int) -> TranslationRubricCriterion:
        return TranslationRubricCriterion(
            key=key,
            name=key.replace('_', ' ').title(),
            description=f'Evaluate {key}.',
            weight_percentage=weight,
            required=True,
            fixed_comments=tuple(
                TranslationRubricComment(
                    id=f'{key}-{level}', level=level, text=f'Fixed comment {level}'
                )
                for level in (0, 25, 50, 75, 100)
            ),
            inconclusive_comment=TranslationInconclusiveComment(
                id=f'{key}-unknown', text='Inconclusivo'
            ),
        )

    return Activity.create(
        id='01SHF000000000000000000093',
        competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Atividade mista de tradução',
        objective='Aprender',
        questions=(*questions, translation),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                TranslationRubricEvaluationPart(
                    question_key='q3',
                    weight_percentage=40,
                    criteria=(
                        rubric_criterion('semantic_preservation', 70),
                        rubric_criterion('grammatical_adequacy', 30),
                    ),
                ),
            )
        ),
    )
