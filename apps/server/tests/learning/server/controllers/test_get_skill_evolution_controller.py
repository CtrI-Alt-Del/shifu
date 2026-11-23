from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.curriculum.database.logic_programming_seed import LOGIC_SKILL_ID
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.fakers.identity.entities.account_faker import AccountFaker
from shifu.fakers.learning.entities import (
    ActivityAttemptFaker,
    ActivityEvaluationFaker,
    GoalFaker,
    SkillExperienceFaker,
)
from shifu.fakers.learning.structures import SkillCompletionSummaryFaker
from shifu.identity.database.sqlalchemy.identity_database import (
    SqlalchemyIdentityDatabase,
)
from shifu.learning.core.domain.entities import ActivityAttempt, ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import ConceptObservation
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ADAPTIVE_LAB_SKILL_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response

ACCOUNT_A = '01SHF000000000000000008001'
ACCOUNT_B = '01SHF000000000000000008002'
GOAL_A = '01SHF000000000000000008101'
GOAL_A_SECOND = '01SHF000000000000000008102'
GOAL_B = '01SHF000000000000000008103'
EXP_LEARNING = '01SHF000000000000000008201'
EXP_COMPLETED = '01SHF000000000000000008202'
EXP_WITHOUT_EVIDENCE = '01SHF000000000000000008203'
EXP_REMOVED = '01SHF000000000000000008204'
EXP_OTHER_ACCOUNT = '01SHF000000000000000008205'
UNKNOWN_EXP = '01SHF000000000000000008299'
NOT_FOUND_BODY = {
    'code': 'not_found',
    'message': 'A experiência da habilidade não foi encontrada.',
}


class _Authentication:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        accounts = {'token-a': ACCOUNT_A, 'token-b': ACCOUNT_B}
        account_id = accounts.get(access_token)
        if account_id is None:
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=account_id,
            display_name='Pessoa Aprendente',
            time_zone='America/Sao_Paulo',
            session_id=f'learning-evolution-{access_token}',
            token_access_version=1,
            account_access_version=1,
        )


def _id(number: int) -> str:
    return f'01SHF{number:021d}'


def _at(month: int, day: int, hour: int = 12) -> datetime:
    return datetime(2026, month, day, hour, 0, tzinfo=UTC)


def _path(experience_id: str) -> str:
    return f'/learning/panorama/skill-experiences/{experience_id}/evolution'


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    with SqlalchemyIdentityDatabase(postgres_database.engine).transaction() as repos:
        for account_id in (ACCOUNT_A, ACCOUNT_B):
            if repos.accounts.find_by_id(account_id) is None:
                repos.accounts.add(AccountFaker.fake(id=account_id, access_version=1))
    _seed_curriculum(postgres_database)
    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _Authentication()
    application.state.learning_database = SqlalchemyLearningDatabase(
        postgres_database.engine
    )
    application.state.curriculum_content_provider = DatabaseCurriculumContentProvider(
        SqlalchemyCurriculumDatabase(postgres_database.engine)
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def learning_database(
    application: FastAPI, postgres_database: PostgresDatabase
) -> SqlalchemyLearningDatabase:
    return SqlalchemyLearningDatabase(postgres_database.engine)


@pytest.fixture
def seeded(
    application: FastAPI, learning_database: SqlalchemyLearningDatabase
) -> SqlalchemyLearningDatabase:
    content = application.state.curriculum_content_provider.get_skill_content(
        LOGIC_SKILL_ID
    )
    assert content is not None
    concepts = [
        (competency.id, concept.id)
        for competency in content.competencies
        for concept in competency.concepts
    ]
    _seed_learning(learning_database, concepts)
    return learning_database


class TestGetSkillEvolutionController:
    def test_should_return_the_base_and_one_point_per_changed_official_learning_result(
        self, client: TestClient, seeded: SqlalchemyLearningDatabase
    ) -> None:
        response = _get(client, EXP_LEARNING, 'token-a')

        assert response.status_code == 200, response.text
        assert response.json() == {
            'skillExperienceId': EXP_LEARNING,
            'points': [
                {
                    'occurredAt': '2026-10-20T14:00:00Z',
                    'result': 50.0,
                    'isPartial': True,
                    'isBaseline': True,
                },
                {
                    'occurredAt': '2026-11-05T12:00:00Z',
                    'result': 56.5,
                    'isPartial': True,
                    'isBaseline': False,
                },
                {
                    'occurredAt': '2026-11-08T12:00:00Z',
                    'result': 63.0,
                    'isPartial': True,
                    'isBaseline': False,
                },
            ],
        }

    def test_should_end_a_completed_experience_at_its_completing_evaluation_without_a_base(
        self, client: TestClient, seeded: SqlalchemyLearningDatabase
    ) -> None:
        response = _get(client, EXP_COMPLETED, 'token-a')

        assert response.status_code == 200, response.text
        assert response.json() == {
            'skillExperienceId': EXP_COMPLETED,
            'points': [
                {
                    'occurredAt': '2026-10-01T12:00:00Z',
                    'result': 70.0,
                    'isPartial': True,
                    'isBaseline': False,
                },
                {
                    'occurredAt': '2026-10-02T12:00:00Z',
                    'result': 92.0,
                    'isPartial': True,
                    'isBaseline': False,
                },
            ],
        }

    def test_should_return_an_empty_series_for_an_experience_without_evidence(
        self, client: TestClient, seeded: SqlalchemyLearningDatabase
    ) -> None:
        response = _get(client, EXP_WITHOUT_EVIDENCE, 'token-a')

        assert response.status_code == 200, response.text
        assert response.json() == {
            'skillExperienceId': EXP_WITHOUT_EVIDENCE,
            'points': [],
        }

    def test_should_return_only_the_series_of_the_authenticated_account(
        self, client: TestClient, seeded: SqlalchemyLearningDatabase
    ) -> None:
        response = _get(client, EXP_OTHER_ACCOUNT, 'token-b')

        assert response.status_code == 200, response.text
        assert response.json() == {
            'skillExperienceId': EXP_OTHER_ACCOUNT,
            'points': [
                {
                    'occurredAt': '2026-10-09T12:00:00Z',
                    'result': 81.0,
                    'isPartial': True,
                    'isBaseline': False,
                }
            ],
        }

    def test_should_answer_the_same_not_found_body_for_a_foreign_removed_or_unknown_experience(
        self, client: TestClient, seeded: SqlalchemyLearningDatabase
    ) -> None:
        with seeded.transaction() as repositories:
            removed = repositories.skill_experiences.find_by_id(EXP_REMOVED)
            assert removed is not None
            repositories.skill_experiences.remove(removed)

        foreign = _get(client, EXP_OTHER_ACCOUNT, 'token-a')
        reversed_foreign = _get(client, EXP_LEARNING, 'token-b')
        removed_response = _get(client, EXP_REMOVED, 'token-a')
        unknown = _get(client, UNKNOWN_EXP, 'token-a')
        malformed = _get(client, 'not-an-identifier', 'token-a')

        for response in (
            foreign,
            reversed_foreign,
            removed_response,
            unknown,
            malformed,
        ):
            assert response.status_code == 404, response.text
            assert response.json() == NOT_FOUND_BODY

    @pytest.mark.parametrize(
        'headers',
        [None, {'Authorization': 'Bearer invalid-token'}],
        ids=['without credentials', 'invalid credentials'],
    )
    def test_should_return_401_without_data_when_unauthenticated(
        self,
        client: TestClient,
        seeded: SqlalchemyLearningDatabase,
        headers: dict[str, str] | None,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _path(EXP_LEARNING), headers=headers
            ),
        )

        assert response.status_code == 401
        assert 'points' not in response.json()


def _get(client: TestClient, experience_id: str, token: str) -> 'Response':
    return cast(
        'Response',
        client.get(  # pyright: ignore[reportUnknownMemberType]
            _path(experience_id),
            headers={'Authorization': f'Bearer {token}'},
        ),
    )


def _seed_curriculum(database: PostgresDatabase) -> None:
    seed = build_development_seed()
    curriculum_database = SqlalchemyCurriculumDatabase(database.engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))


def _learning_attempt(
    number: int,
    experience_id: str,
    kind: ActivityAttemptKind,
    completed_at: datetime,
    *,
    status: ActivityEvaluationStatus = ActivityEvaluationStatus.COMPLETED,
    progress_after: str | None = None,
) -> tuple[ActivityAttempt, ActivityEvaluation]:
    submitted_at = completed_at - timedelta(minutes=10)
    attempt = ActivityAttemptFaker.fake(
        id=_id(8300 + number),
        skill_experience_id=experience_id,
        activity_id=_id(8350 + number),
        kind=kind,
        submitted_at=submitted_at,
    )
    evaluation = ActivityEvaluationFaker.fake(
        id=_id(8400 + number),
        attempt_id=attempt.id,
        status=status,
        started_at=submitted_at,
        completed_at=(
            completed_at if status is ActivityEvaluationStatus.COMPLETED else None
        ),
        progress_after=(
            Decimal(progress_after) if progress_after is not None else None
        ),
    )
    return attempt, evaluation


def _seed_learning(
    database: SqlalchemyLearningDatabase, concepts: list[tuple[str, str]]
) -> None:
    learning = ActivityAttemptKind.LEARNING
    pending = ActivityEvaluationStatus.PENDING
    failed = ActivityEvaluationStatus.FAILED
    goals = [
        GoalFaker.fake(id=GOAL_A, account_id=ACCOUNT_A, title='Carreira em dados'),
        GoalFaker.fake(
            id=GOAL_A_SECOND, account_id=ACCOUNT_A, title='Aprender a programar'
        ),
        GoalFaker.fake(id=GOAL_B, account_id=ACCOUNT_B, title='Outra conta'),
    ]
    completed_started = _at(9, 14)
    completed_at = _at(10, 2)
    experiences = [
        SkillExperienceFaker.fake(
            id=EXP_LEARNING,
            goal_id=GOAL_A,
            skill_id=LOGIC_SKILL_ID,
            status=SkillExperienceStatus.LEARNING,
            created_at=_at(10, 19),
            started_at=_at(10, 20),
        ),
        SkillExperienceFaker.fake(
            id=EXP_COMPLETED,
            goal_id=GOAL_A_SECOND,
            skill_id=LOGIC_SKILL_ID,
            status=SkillExperienceStatus.COMPLETED,
            created_at=_at(9, 13),
            started_at=completed_started,
            completed_at=completed_at,
            completion_summary=SkillCompletionSummaryFaker.fake(
                final_progress=Decimal('92'),
                started_at=completed_started,
                completed_at=completed_at,
            ),
        ),
        SkillExperienceFaker.fake(
            id=EXP_WITHOUT_EVIDENCE,
            goal_id=GOAL_A,
            skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
            status=SkillExperienceStatus.DIAGNOSING,
            created_at=_at(11, 1),
            started_at=_at(11, 2),
        ),
        SkillExperienceFaker.fake(
            id=EXP_REMOVED,
            goal_id=GOAL_A_SECOND,
            skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
            status=SkillExperienceStatus.LEARNING,
            created_at=_at(10, 1),
            started_at=_at(10, 2),
        ),
        SkillExperienceFaker.fake(
            id=EXP_OTHER_ACCOUNT,
            goal_id=GOAL_B,
            skill_id=LOGIC_SKILL_ID,
            status=SkillExperienceStatus.LEARNING,
            created_at=_at(10, 1),
            started_at=_at(10, 2),
        ),
    ]
    diagnostic_at = datetime(2026, 10, 20, 14, 0, tzinfo=UTC)
    diagnostic_attempt = ActivityAttemptFaker.fake(
        id=_id(8300),
        skill_experience_id=EXP_LEARNING,
        activity_id=_id(8350),
        kind=ActivityAttemptKind.DIAGNOSTIC,
        submitted_at=diagnostic_at - timedelta(minutes=10),
    )
    diagnostic_evaluation = ActivityEvaluationFaker.fake(
        id=_id(8400),
        attempt_id=diagnostic_attempt.id,
        started_at=diagnostic_at - timedelta(minutes=10),
        completed_at=diagnostic_at,
    )
    attempts_and_evaluations = [
        (diagnostic_attempt, diagnostic_evaluation),
        _learning_attempt(
            1, EXP_LEARNING, learning, _at(11, 5), progress_after='56.50'
        ),
        _learning_attempt(
            2, EXP_LEARNING, learning, _at(11, 6), progress_after='56.50'
        ),
        _learning_attempt(3, EXP_LEARNING, learning, _at(11, 8), progress_after='63'),
        _learning_attempt(4, EXP_LEARNING, learning, _at(11, 9), status=pending),
        _learning_attempt(5, EXP_LEARNING, learning, _at(11, 10), status=failed),
        _learning_attempt(
            6,
            EXP_LEARNING,
            ActivityAttemptKind.REVIEW,
            _at(11, 12),
            progress_after='99',
        ),
        _learning_attempt(7, EXP_COMPLETED, learning, _at(10, 1), progress_after='70'),
        _learning_attempt(8, EXP_COMPLETED, learning, _at(10, 2), progress_after='92'),
        _learning_attempt(
            9,
            EXP_COMPLETED,
            ActivityAttemptKind.REVIEW,
            _at(10, 10),
            progress_after='100',
        ),
        _learning_attempt(10, EXP_REMOVED, learning, _at(10, 5), progress_after='40'),
        _learning_attempt(
            11, EXP_OTHER_ACCOUNT, learning, _at(10, 9), progress_after='81'
        ),
    ]
    observations_by_competency: dict[str, list[ConceptObservation]] = {}
    for competency_id, concept_id in concepts:
        observations_by_competency.setdefault(competency_id, []).append(
            ConceptObservation(
                attempt_id=diagnostic_attempt.id,
                activity_id=diagnostic_attempt.activity_id,
                concept_id=concept_id,
                difficulty=ActivityDifficulty.EASY,
                first_submitted_at=diagnostic_at - timedelta(minutes=10),
                submitted_at=diagnostic_at - timedelta(minutes=10),
                completed_at=diagnostic_at,
                question_scores=(Decimal('50'),),
                diagnostic=True,
            )
        )
    with database.transaction() as repositories:
        repositories.goals.add_many(goals)
        repositories.skill_experiences.add_many(experiences)
        repositories.activity_attempts.add_many(
            [attempt for attempt, _ in attempts_and_evaluations]
        )
        repositories.activity_evaluations.add_many(
            [evaluation for _, evaluation in attempts_and_evaluations]
        )
        for competency_id, observations in observations_by_competency.items():
            repositories.concept_observations.add_many(
                EXP_LEARNING, competency_id, tuple(observations)
            )
