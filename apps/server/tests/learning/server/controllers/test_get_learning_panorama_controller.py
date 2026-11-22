from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.curriculum.database.logic_programming_seed import (
    LOGIC_SKILL_ID,
    build_logic_programming_seed,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.fakers.learning.entities import (
    ActivityAttemptFaker,
    ActivityEvaluationFaker,
    CompetencyProgressFaker,
    GoalFaker,
    SkillExperienceFaker,
)
from shifu.fakers.learning.structures import SkillCompletionSummaryFaker
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
    Goal,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response

PYRAMID_SKILL_ID = '01SHFRM0000000000000004300'
ACCOUNT_A = '01SHF000000000000000007001'
ACCOUNT_B = '01SHF000000000000000007002'
EMPTY_ACCOUNT = '01SHF000000000000000007003'
NOW = datetime(2026, 11, 18, 15, 0, tzinfo=UTC)  # a Wednesday
PANORAMA_PATH = '/learning/panorama'
SKILL_NAMES = {skill.id: skill.name for skill in build_development_seed().skills}
LOGIC_COMPETENCIES = sorted(
    build_logic_programming_seed().competencies, key=lambda item: item.position
)

GOAL_DATA = '01SHF000000000000000007101'
GOAL_CODING = '01SHF000000000000000007102'
GOAL_FUNDAMENTALS = '01SHF000000000000000007103'
GOAL_OTHER = '01SHF000000000000000007104'
EXP_LOGIC_IN_DATA = '01SHF000000000000000007201'
EXP_PYRAMID_DIAGNOSING = '01SHF000000000000000007202'
EXP_LOGIC_IN_CODING = '01SHF000000000000000007203'
EXP_ADAPTIVE_COMPLETED = '01SHF000000000000000007204'
EXP_LOGIC_LEARNING = '01SHF000000000000000007205'
EXP_PYRAMID_NOT_STARTED = '01SHF000000000000000007206'
EXP_ADAPTIVE_REMOVED = '01SHF000000000000000007207'
EXP_OTHER_ACCOUNT = '01SHF000000000000000007208'
TITLES = {
    GOAL_DATA: 'Carreira em dados',
    GOAL_CODING: 'Aprender a programar',
    GOAL_FUNDAMENTALS: 'Fundamentos de programação',
    GOAL_OTHER: 'Objetivo de outra conta',
}


class _Authentication:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        accounts = {
            'token-a': ACCOUNT_A,
            'token-b': ACCOUNT_B,
            'token-empty': EMPTY_ACCOUNT,
        }
        account_id = accounts.get(access_token)
        if account_id is None:
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=account_id,
            display_name='Pessoa Aprendente',
            time_zone='America/Sao_Paulo',
        )


class _FixedClock:
    def now(self) -> datetime:
        return NOW


def _id(number: int) -> str:
    return f'01SHF{number:021d}'


def _at(
    month: int, day: int, hour: int = 12, minute: int = 0, second: int = 0
) -> datetime:
    return datetime(2026, month, day, hour, minute, second, tzinfo=UTC)


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    _seed_curriculum(postgres_database)
    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _Authentication()
    application.state.learning_database = SqlalchemyLearningDatabase(
        postgres_database.engine
    )
    application.state.curriculum_content_provider = DatabaseCurriculumContentProvider(
        SqlalchemyCurriculumDatabase(postgres_database.engine)
    )
    application.dependency_overrides[LearningPipe.get_clock_provider] = _FixedClock
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


class TestGetLearningPanoramaController:
    def test_should_return_the_documented_panorama_from_real_persistence_after_a_removal(
        self,
        client: TestClient,
        learning_database: SqlalchemyLearningDatabase,
    ) -> None:
        _seed_account_a(learning_database)
        _remove_experience(learning_database, EXP_ADAPTIVE_REMOVED)

        response = _get(client, 'token-a')

        assert response.status_code == 200, response.text
        assert response.json() == _expected_panorama_of_account_a()

    def test_should_never_report_an_average_or_result_of_objectives_or_of_the_user(
        self,
        client: TestClient,
        learning_database: SqlalchemyLearningDatabase,
    ) -> None:
        _seed_account_a(learning_database)

        body = _get(client, 'token-a').json()

        assert sorted(body) == [
            'completedSkillCount',
            'completedSkills',
            'defaultEvolutionSkillExperienceId',
            'evolutionOptions',
            'hasGoals',
            'masteredCompetencyCount',
            'recentMasteries',
            'resumeItems',
            'stageDistribution',
            'weeklyEvaluatedActivities',
        ]
        assert sorted(body['stageDistribution']) == [
            'completed',
            'diagnosing',
            'goalCount',
            'learning',
            'notStarted',
        ]

    def test_should_return_only_the_data_of_the_authenticated_account(
        self,
        client: TestClient,
        learning_database: SqlalchemyLearningDatabase,
    ) -> None:
        _seed_account_a(learning_database)
        _seed_account_b(learning_database)

        response = _get(client, 'token-b')

        assert response.status_code == 200, response.text
        assert response.json() == {
            'hasGoals': True,
            'completedSkillCount': 1,
            'masteredCompetencyCount': 1,
            'stageDistribution': {
                'notStarted': 0,
                'diagnosing': 0,
                'learning': 0,
                'completed': 1,
                'goalCount': 1,
            },
            'resumeItems': [],
            'weeklyEvaluatedActivities': _weeks({7: 1}),
            'evolutionOptions': [
                {
                    'skillExperienceId': EXP_OTHER_ACCOUNT,
                    'goalTitle': TITLES[GOAL_OTHER],
                    'skillName': SKILL_NAMES[LOGIC_SKILL_ID],
                    'status': 'completed',
                }
            ],
            'defaultEvolutionSkillExperienceId': EXP_OTHER_ACCOUNT,
            'completedSkills': [
                {
                    'skillExperienceId': EXP_OTHER_ACCOUNT,
                    'goalId': GOAL_OTHER,
                    'goalTitle': TITLES[GOAL_OTHER],
                    'skillId': LOGIC_SKILL_ID,
                    'skillName': SKILL_NAMES[LOGIC_SKILL_ID],
                    'finalResult': 88.0,
                    'completedOn': '2026-10-10',
                }
            ],
            'recentMasteries': [
                {
                    'skillExperienceId': EXP_OTHER_ACCOUNT,
                    'goalId': GOAL_OTHER,
                    'goalTitle': TITLES[GOAL_OTHER],
                    'skillId': LOGIC_SKILL_ID,
                    'skillName': SKILL_NAMES[LOGIC_SKILL_ID],
                    'competencyId': LOGIC_COMPETENCIES[0].id,
                    'competencyName': LOGIC_COMPETENCIES[0].name,
                    'masteredOn': '2026-10-09',
                }
            ],
        }
        assert GOAL_DATA not in response.text
        assert EXP_LOGIC_LEARNING not in response.text

    def test_should_return_an_empty_panorama_for_an_account_without_objectives(
        self,
        client: TestClient,
        learning_database: SqlalchemyLearningDatabase,
    ) -> None:
        _seed_account_a(learning_database)

        response = _get(client, 'token-empty')

        assert response.status_code == 200, response.text
        assert response.json() == {
            'hasGoals': False,
            'completedSkillCount': 0,
            'masteredCompetencyCount': 0,
            'stageDistribution': {
                'notStarted': 0,
                'diagnosing': 0,
                'learning': 0,
                'completed': 0,
                'goalCount': 0,
            },
            'resumeItems': [],
            'weeklyEvaluatedActivities': _weeks({}),
            'evolutionOptions': [],
            'defaultEvolutionSkillExperienceId': None,
            'completedSkills': [],
            'recentMasteries': [],
        }

    def test_should_stop_counting_a_removed_experience_in_every_learning_value(
        self,
        client: TestClient,
        learning_database: SqlalchemyLearningDatabase,
    ) -> None:
        _seed_account_a(learning_database)

        before = _get(client, 'token-a').json()
        _remove_experience(learning_database, EXP_ADAPTIVE_REMOVED)
        after = _get(client, 'token-a').json()

        assert before['stageDistribution']['learning'] == 2
        assert before['masteredCompetencyCount'] == 6
        assert before['weeklyEvaluatedActivities'] == _weeks({0: 1, 6: 2, 7: 2})
        assert [item['skillExperienceId'] for item in before['resumeItems']] == [
            EXP_ADAPTIVE_REMOVED,
            EXP_LOGIC_LEARNING,
            EXP_PYRAMID_DIAGNOSING,
        ]
        assert after['stageDistribution']['learning'] == 1
        assert after['masteredCompetencyCount'] == 5
        assert after['weeklyEvaluatedActivities'] == _weeks({0: 1, 6: 2, 7: 1})
        assert [item['skillExperienceId'] for item in after['resumeItems']] == [
            EXP_LOGIC_LEARNING,
            EXP_PYRAMID_DIAGNOSING,
        ]
        assert EXP_ADAPTIVE_REMOVED not in str(after)

    def test_should_stop_counting_every_experience_of_a_removed_objective(
        self,
        client: TestClient,
        learning_database: SqlalchemyLearningDatabase,
    ) -> None:
        _seed_account_a(learning_database)

        with learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(GOAL_FUNDAMENTALS)
            assert goal is not None
            repositories.goals.remove(goal)
        body = _get(client, 'token-a').json()

        assert body['stageDistribution'] == {
            'notStarted': 0,
            'diagnosing': 1,
            'learning': 0,
            'completed': 3,
            'goalCount': 2,
        }
        assert [item['skillExperienceId'] for item in body['resumeItems']] == [
            EXP_PYRAMID_DIAGNOSING
        ]
        assert body['defaultEvolutionSkillExperienceId'] is None

    @pytest.mark.parametrize(
        'headers',
        [None, {'Authorization': 'Bearer invalid-token'}],
        ids=['without credentials', 'invalid credentials'],
    )
    def test_should_return_401_without_data_when_unauthenticated(
        self,
        client: TestClient,
        learning_database: SqlalchemyLearningDatabase,
        headers: dict[str, str] | None,
    ) -> None:
        _seed_account_a(learning_database)

        response = cast(
            'Response',
            client.get(PANORAMA_PATH, headers=headers),  # pyright: ignore[reportUnknownMemberType]
        )

        assert response.status_code == 401
        assert 'hasGoals' not in response.json()


def _get(client: TestClient, token: str) -> 'Response':
    return cast(
        'Response',
        client.get(  # pyright: ignore[reportUnknownMemberType]
            PANORAMA_PATH,
            headers={'Authorization': f'Bearer {token}'},
        ),
    )


def _weeks(counts: dict[int, int]) -> list[dict[str, object]]:
    starts = (
        '2026-09-28',
        '2026-10-05',
        '2026-10-12',
        '2026-10-19',
        '2026-10-26',
        '2026-11-02',
        '2026-11-09',
        '2026-11-16',
    )
    return [
        {'weekStart': start, 'count': counts.get(index, 0)}
        for index, start in enumerate(starts)
    ]


def _expected_panorama_of_account_a() -> dict[str, object]:
    logic = SKILL_NAMES[LOGIC_SKILL_ID]
    return {
        'hasGoals': True,
        'completedSkillCount': 2,
        'masteredCompetencyCount': 5,
        'stageDistribution': {
            'notStarted': 1,
            'diagnosing': 1,
            'learning': 1,
            'completed': 3,
            'goalCount': 3,
        },
        'resumeItems': [
            {
                'skillExperienceId': EXP_LOGIC_LEARNING,
                'goalId': GOAL_FUNDAMENTALS,
                'goalTitle': TITLES[GOAL_FUNDAMENTALS],
                'skillId': LOGIC_SKILL_ID,
                'skillName': logic,
                'status': 'learning',
                'focusCompetencyName': LOGIC_COMPETENCIES[1].name,
                'lastSubmittedAt': '2026-11-16T03:30:00Z',
            },
            {
                'skillExperienceId': EXP_PYRAMID_DIAGNOSING,
                'goalId': GOAL_DATA,
                'goalTitle': TITLES[GOAL_DATA],
                'skillId': PYRAMID_SKILL_ID,
                'skillName': SKILL_NAMES[PYRAMID_SKILL_ID],
                'status': 'diagnosing',
                'focusCompetencyName': None,
                'lastSubmittedAt': None,
            },
        ],
        'weeklyEvaluatedActivities': _weeks({0: 1, 6: 2, 7: 1}),
        'evolutionOptions': [
            {
                'skillExperienceId': EXP_LOGIC_LEARNING,
                'goalTitle': TITLES[GOAL_FUNDAMENTALS],
                'skillName': logic,
                'status': 'learning',
            },
            {
                'skillExperienceId': EXP_PYRAMID_DIAGNOSING,
                'goalTitle': TITLES[GOAL_DATA],
                'skillName': SKILL_NAMES[PYRAMID_SKILL_ID],
                'status': 'diagnosing',
            },
            {
                'skillExperienceId': EXP_ADAPTIVE_COMPLETED,
                'goalTitle': TITLES[GOAL_CODING],
                'skillName': SKILL_NAMES[SEED_ADAPTIVE_LAB_SKILL_ID],
                'status': 'completed',
            },
            {
                'skillExperienceId': EXP_LOGIC_IN_CODING,
                'goalTitle': TITLES[GOAL_CODING],
                'skillName': logic,
                'status': 'completed',
            },
            {
                'skillExperienceId': EXP_LOGIC_IN_DATA,
                'goalTitle': TITLES[GOAL_DATA],
                'skillName': logic,
                'status': 'completed',
            },
        ],
        'defaultEvolutionSkillExperienceId': EXP_LOGIC_LEARNING,
        'completedSkills': [
            {
                'skillExperienceId': EXP_ADAPTIVE_COMPLETED,
                'goalId': GOAL_CODING,
                'goalTitle': TITLES[GOAL_CODING],
                'skillId': SEED_ADAPTIVE_LAB_SKILL_ID,
                'skillName': SKILL_NAMES[SEED_ADAPTIVE_LAB_SKILL_ID],
                'finalResult': 77.0,
                'completedOn': '2026-10-20',
            },
            {
                'skillExperienceId': EXP_LOGIC_IN_CODING,
                'goalId': GOAL_CODING,
                'goalTitle': TITLES[GOAL_CODING],
                'skillId': LOGIC_SKILL_ID,
                'skillName': logic,
                'finalResult': 84.5,
                'completedOn': '2026-10-02',
            },
            {
                'skillExperienceId': EXP_LOGIC_IN_DATA,
                'goalId': GOAL_DATA,
                'goalTitle': TITLES[GOAL_DATA],
                'skillId': LOGIC_SKILL_ID,
                'skillName': logic,
                'finalResult': 91.0,
                'completedOn': '2026-09-12',
            },
        ],
        'recentMasteries': [
            _mastery(EXP_LOGIC_LEARNING, GOAL_FUNDAMENTALS, 0, '2026-10-25'),
            _mastery(EXP_LOGIC_IN_CODING, GOAL_CODING, 2, '2026-10-02'),
            _mastery(EXP_LOGIC_IN_CODING, GOAL_CODING, 1, '2026-09-30'),
            _mastery(EXP_LOGIC_IN_CODING, GOAL_CODING, 0, '2026-09-28'),
            _mastery(EXP_LOGIC_IN_DATA, GOAL_DATA, 4, '2026-09-12'),
        ],
    }


def _mastery(
    experience_id: str, goal_id: str, competency_index: int, mastered_on: str
) -> dict[str, object]:
    competency = LOGIC_COMPETENCIES[competency_index]
    return {
        'skillExperienceId': experience_id,
        'goalId': goal_id,
        'goalTitle': TITLES[goal_id],
        'skillId': LOGIC_SKILL_ID,
        'skillName': SKILL_NAMES[LOGIC_SKILL_ID],
        'competencyId': competency.id,
        'competencyName': competency.name,
        'masteredOn': mastered_on,
    }


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


def _remove_experience(
    database: SqlalchemyLearningDatabase, experience_id: str
) -> None:
    with database.transaction() as repositories:
        experience = repositories.skill_experiences.find_by_id(experience_id)
        assert experience is not None
        repositories.skill_experiences.remove(experience)


def _experience(
    experience_id: str,
    goal_id: str,
    skill_id: str,
    status: SkillExperienceStatus,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    final_result: str = '90',
) -> SkillExperience:
    return SkillExperienceFaker.fake(
        id=experience_id,
        goal_id=goal_id,
        skill_id=skill_id,
        status=status,
        created_at=_at(9, 1),
        started_at=started_at,
        completed_at=completed_at,
        completion_summary=(
            SkillCompletionSummaryFaker.fake(
                final_progress=Decimal(final_result),
                started_at=started_at or _at(9, 1),
                completed_at=completed_at or _at(9, 1),
            )
            if status is SkillExperienceStatus.COMPLETED
            else None
        ),
    )


def _progress(
    number: int,
    experience_id: str,
    competency_id: str,
    status: CompetencyProgressStatus,
    mastered_at: datetime | None = None,
    verification_cause: str | None = None,
) -> CompetencyProgress:
    return CompetencyProgressFaker.fake(
        id=_id(7500 + number),
        skill_experience_id=experience_id,
        competency_id=competency_id,
        status=status,
        mastered_at=mastered_at,
        verification_cause=verification_cause,
    )


def _attempt(
    number: int,
    experience_id: str,
    kind: ActivityAttemptKind,
    submitted_at: datetime,
    status: ActivityEvaluationStatus,
) -> tuple[ActivityAttempt, ActivityEvaluation]:
    attempt = ActivityAttemptFaker.fake(
        id=_id(7300 + number),
        skill_experience_id=experience_id,
        competency_id=LOGIC_COMPETENCIES[0].id,
        activity_id=_id(7350 + number),
        kind=kind,
        submitted_at=submitted_at,
    )
    evaluation = ActivityEvaluationFaker.fake(
        id=_id(7400 + number),
        attempt_id=attempt.id,
        status=status,
        started_at=submitted_at,
        completed_at=(
            submitted_at if status is ActivityEvaluationStatus.COMPLETED else None
        ),
    )
    return attempt, evaluation


def _seed_account_a(database: SqlalchemyLearningDatabase) -> None:
    completed = ActivityEvaluationStatus.COMPLETED
    mastered = CompetencyProgressStatus.MASTERED
    learning = CompetencyProgressStatus.LEARNING
    c1, c2, c3, c4, c5 = (item.id for item in LOGIC_COMPETENCIES)
    goals = [
        GoalFaker.fake(id=goal_id, account_id=ACCOUNT_A, title=TITLES[goal_id])
        for goal_id in (GOAL_DATA, GOAL_CODING, GOAL_FUNDAMENTALS)
    ]
    experiences = [
        _experience(
            EXP_LOGIC_IN_DATA,
            GOAL_DATA,
            LOGIC_SKILL_ID,
            SkillExperienceStatus.COMPLETED,
            _at(9, 2, 23, 30),
            _at(9, 13, 2),
            '91',
        ),
        _experience(
            EXP_PYRAMID_DIAGNOSING,
            GOAL_DATA,
            PYRAMID_SKILL_ID,
            SkillExperienceStatus.DIAGNOSING,
            _at(11, 1),
        ),
        _experience(
            EXP_LOGIC_IN_CODING,
            GOAL_CODING,
            LOGIC_SKILL_ID,
            SkillExperienceStatus.COMPLETED,
            _at(9, 14),
            _at(10, 2, 15),
            '84.5',
        ),
        _experience(
            EXP_ADAPTIVE_COMPLETED,
            GOAL_CODING,
            SEED_ADAPTIVE_LAB_SKILL_ID,
            SkillExperienceStatus.COMPLETED,
            _at(10, 5),
            _at(10, 20),
            '77',
        ),
        _experience(
            EXP_LOGIC_LEARNING,
            GOAL_FUNDAMENTALS,
            LOGIC_SKILL_ID,
            SkillExperienceStatus.LEARNING,
            _at(10, 20),
        ),
        _experience(
            EXP_PYRAMID_NOT_STARTED,
            GOAL_FUNDAMENTALS,
            PYRAMID_SKILL_ID,
            SkillExperienceStatus.NOT_STARTED,
        ),
        _experience(
            EXP_ADAPTIVE_REMOVED,
            GOAL_FUNDAMENTALS,
            SEED_ADAPTIVE_LAB_SKILL_ID,
            SkillExperienceStatus.LEARNING,
            _at(11, 5),
        ),
    ]
    progresses = [
        _progress(1, EXP_LOGIC_IN_DATA, c1, mastered, _at(9, 4)),
        _progress(2, EXP_LOGIC_IN_DATA, c2, mastered, _at(9, 6, 1)),
        _progress(3, EXP_LOGIC_IN_DATA, c3, mastered, _at(9, 8, 15)),
        _progress(4, EXP_LOGIC_IN_DATA, c4, mastered, _at(9, 10, 2, 30)),
        _progress(5, EXP_LOGIC_IN_DATA, c5, mastered, _at(9, 13, 2)),
        _progress(6, EXP_LOGIC_IN_CODING, c1, mastered, _at(9, 28)),
        _progress(7, EXP_LOGIC_IN_CODING, c2, mastered, _at(9, 30)),
        _progress(8, EXP_LOGIC_IN_CODING, c3, mastered, _at(10, 2)),
        _progress(9, EXP_LOGIC_IN_CODING, c4, learning),
        _progress(10, EXP_LOGIC_IN_CODING, c5, learning),
        _progress(11, EXP_LOGIC_LEARNING, c1, mastered, _at(10, 25)),
        _progress(12, EXP_LOGIC_LEARNING, c2, mastered, _at(10, 26), 'evidence'),
        _progress(
            13,
            EXP_ADAPTIVE_REMOVED,
            SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            mastered,
            _at(11, 17),
        ),
    ]
    attempts_and_evaluations = [
        # Sunday 23:30 in Sao Paulo, Monday 00:30, and two submissions around
        # the window start (Monday 2026-09-28 00:00 local).
        _attempt(
            1,
            EXP_LOGIC_LEARNING,
            ActivityAttemptKind.LEARNING,
            _at(11, 16, 2, 30),
            completed,
        ),
        _attempt(
            2,
            EXP_LOGIC_LEARNING,
            ActivityAttemptKind.LEARNING,
            _at(11, 16, 3, 30),
            completed,
        ),
        _attempt(
            3,
            EXP_LOGIC_LEARNING,
            ActivityAttemptKind.REVIEW,
            _at(11, 10),
            completed,
        ),
        _attempt(
            4,
            EXP_LOGIC_LEARNING,
            ActivityAttemptKind.DIAGNOSTIC,
            _at(11, 11),
            completed,
        ),
        _attempt(
            5,
            EXP_LOGIC_LEARNING,
            ActivityAttemptKind.LEARNING,
            _at(11, 12),
            ActivityEvaluationStatus.PENDING,
        ),
        _attempt(
            6,
            EXP_LOGIC_LEARNING,
            ActivityAttemptKind.LEARNING,
            _at(11, 13),
            ActivityEvaluationStatus.FAILED,
        ),
        _attempt(
            7,
            EXP_LOGIC_LEARNING,
            ActivityAttemptKind.LEARNING,
            _at(9, 20),
            completed,
        ),
        _attempt(
            8,
            EXP_LOGIC_LEARNING,
            ActivityAttemptKind.LEARNING,
            _at(9, 28, 3, 0, 0),
            completed,
        ),
        _attempt(
            9,
            EXP_LOGIC_LEARNING,
            ActivityAttemptKind.LEARNING,
            _at(9, 28, 2, 59, 59),
            completed,
        ),
        _attempt(
            10,
            EXP_ADAPTIVE_REMOVED,
            ActivityAttemptKind.LEARNING,
            _at(11, 17),
            completed,
        ),
    ]
    _persist(
        database,
        goals,
        experiences,
        progresses,
        attempts_and_evaluations,
    )


def _seed_account_b(database: SqlalchemyLearningDatabase) -> None:
    _persist(
        database,
        [GoalFaker.fake(id=GOAL_OTHER, account_id=ACCOUNT_B, title=TITLES[GOAL_OTHER])],
        [
            _experience(
                EXP_OTHER_ACCOUNT,
                GOAL_OTHER,
                LOGIC_SKILL_ID,
                SkillExperienceStatus.COMPLETED,
                _at(10, 1),
                _at(10, 10),
                '88',
            )
        ],
        [
            _progress(
                20,
                EXP_OTHER_ACCOUNT,
                LOGIC_COMPETENCIES[0].id,
                CompetencyProgressStatus.MASTERED,
                _at(10, 9),
            )
        ],
        [
            _attempt(
                20,
                EXP_OTHER_ACCOUNT,
                ActivityAttemptKind.LEARNING,
                _at(11, 17),
                ActivityEvaluationStatus.COMPLETED,
            )
        ],
    )


def _persist(
    database: SqlalchemyLearningDatabase,
    goals: list[Goal],
    experiences: list[SkillExperience],
    progresses: list[CompetencyProgress],
    attempts_and_evaluations: list[tuple[ActivityAttempt, ActivityEvaluation]],
) -> None:
    with database.transaction() as repositories:
        repositories.goals.add_many(goals)
        repositories.skill_experiences.add_many(experiences)
        repositories.competency_progresses.add_many(progresses)
        repositories.activity_attempts.add_many(
            [attempt for attempt, _ in attempts_and_evaluations]
        )
        repositories.activity_evaluations.add_many(
            [evaluation for _, evaluation in attempts_and_evaluations]
        )
