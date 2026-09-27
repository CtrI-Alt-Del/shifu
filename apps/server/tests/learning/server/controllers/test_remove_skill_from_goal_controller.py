from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from threading import Event
from typing import TYPE_CHECKING, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from shifu.app import FastAPIApp
from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.fakers.learning.entities.activity_attempt_faker import ActivityAttemptFaker
from shifu.fakers.learning.entities.activity_evaluation_faker import (
    ActivityEvaluationFaker,
)
from shifu.fakers.learning.entities.competency_progress_faker import (
    CompetencyProgressFaker,
)
from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import (
    AdaptiveConceptState,
    ConceptObservation,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.core.interfaces import LearningDatabaseRepositories
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres_fixture import PostgresDatabase

if TYPE_CHECKING:
    from httpx import Response

HEADERS = {'Authorization': 'Bearer test-token'}


def _client(engine: Engine, account_id: str) -> TestClient:
    app = FastAPIApp.register(engine)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
        AuthenticatedUser(
            account_id=account_id,
            display_name='Pessoa Aprendente',
            time_zone=None,
        )
    )
    return TestClient(app)


class _FailingCommitDatabase:
    def __init__(self, database: SqlalchemyLearningDatabase) -> None:
        self._database = database

    @contextmanager
    def transaction(self) -> Generator[LearningDatabaseRepositories]:
        with self._database.transaction() as repositories:
            yield repositories
            raise RuntimeError('controlled commit failure')


class TestRemoveSkillFromGoalController:
    @pytest.mark.parametrize(
        'status',
        list(SkillExperienceStatus),
    )
    def test_should_remove_experience_and_dependents_in_every_status(
        self,
        postgres_database: PostgresDatabase,
        status: SkillExperienceStatus,
    ) -> None:
        goal = GoalFaker.fake()
        experience = SkillExperienceFaker.fake(goal_id=goal.id, status=status)
        progress = CompetencyProgressFaker.fake(skill_experience_id=experience.id)
        pending_attempt = ActivityAttemptFaker.fake(skill_experience_id=experience.id)
        failed_attempt = ActivityAttemptFaker.fake(skill_experience_id=experience.id)
        pending = ActivityEvaluationFaker.fake(
            attempt_id=pending_attempt.id,
            status=ActivityEvaluationStatus.PENDING,
        )
        failed = ActivityEvaluationFaker.fake(
            attempt_id=failed_attempt.id,
            status=ActivityEvaluationStatus.FAILED,
        )
        now = datetime(2026, 9, 26, tzinfo=UTC)
        concept_id = 'concept-1'
        observation = ConceptObservation(
            attempt_id=pending_attempt.id,
            activity_id=pending_attempt.activity_id,
            concept_id=concept_id,
            difficulty=ActivityDifficulty.EASY,
            first_submitted_at=now,
            submitted_at=now,
            completed_at=now,
            question_scores=(Decimal('100'),),
        )
        concept_state = AdaptiveConceptState(
            concept_id=concept_id,
            initial_progress=Decimal('0'),
            progress=Decimal('100'),
            observed_difficulties=frozenset({ActivityDifficulty.EASY}),
            distinct_activity_ids=frozenset({pending_attempt.activity_id}),
            hard_confirmation=False,
            evidence_verification=False,
            inconclusive_activity_ids=(),
            current_contributions=((pending_attempt.activity_id, Decimal('100')),),
        )
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add_many([experience])
            repositories.competency_progresses.add(progress)
            repositories.activity_attempts.add_many([pending_attempt, failed_attempt])
            repositories.activity_evaluations.add_many([pending, failed])
            repositories.concept_observations.add_many(
                experience.id,
                pending_attempt.competency_id,
                (observation,),
            )
            repositories.concept_states.upsert_many(
                experience.id,
                {concept_id: pending_attempt.competency_id},
                (concept_state,),
                now,
            )

        with _client(postgres_database.engine, goal.account_id) as client:
            response = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills/{experience.skill_id}',
                    headers=HEADERS,
                ),
            )

        assert response.status_code == 204
        assert response.text == ''
        with database.transaction() as repositories:
            assert repositories.goals.find_by_id(goal.id) == goal
            assert repositories.skill_experiences.find_by_id(experience.id) is None
            assert (
                repositories.competency_progresses.find_many_by_skill_experience_id(
                    experience.id
                )
                == []
            )
            assert (
                repositories.activity_attempts.find_many_by_skill_experience_id(
                    experience.id
                )
                == []
            )
            assert (
                repositories.activity_evaluations.find_by_attempt_id(pending_attempt.id)
                is None
            )
            assert (
                repositories.activity_evaluations.find_by_attempt_id(failed_attempt.id)
                is None
            )
            assert (
                repositories.concept_observations.find_many_by_skill_experience_id(
                    experience.id
                )
                == []
            )
            assert (
                repositories.concept_states.find_many_by_skill_experience_id(
                    experience.id
                )
                == []
            )

    def test_should_preserve_sibling_and_other_goal_experience(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        other_goal = GoalFaker.fake(account_id=goal.account_id)
        removed = SkillExperienceFaker.fake(goal_id=goal.id)
        sibling = SkillExperienceFaker.fake(goal_id=goal.id)
        same_skill_elsewhere = SkillExperienceFaker.fake(
            goal_id=other_goal.id,
            skill_id=removed.skill_id,
        )
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.goals.add_many([goal, other_goal])
            repositories.skill_experiences.add_many(
                [removed, sibling, same_skill_elsewhere]
            )

        with _client(postgres_database.engine, goal.account_id) as client:
            response = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills/{removed.skill_id}',
                    headers=HEADERS,
                ),
            )

        assert response.status_code == 204
        with database.transaction() as repositories:
            assert repositories.goals.find_by_id(goal.id) is not None
            assert repositories.skill_experiences.find_by_id(sibling.id) is not None
            assert (
                repositories.skill_experiences.find_by_id(same_skill_elsewhere.id)
                is not None
            )

    @pytest.mark.parametrize('account_id', ['another-account', 'owner'])
    def test_should_return_private_404_without_mutation(
        self,
        postgres_database: PostgresDatabase,
        account_id: str,
    ) -> None:
        goal = GoalFaker.fake(account_id='owner')
        experience = SkillExperienceFaker.fake(goal_id=goal.id)
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add(experience)
        requested_skill_id = (
            experience.skill_id if account_id == 'another-account' else 'missing-skill'
        )

        with _client(postgres_database.engine, account_id) as client:
            first = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills/{requested_skill_id}',
                    headers=HEADERS,
                ),
            )

        assert first.status_code == 404
        with database.transaction() as repositories:
            assert repositories.skill_experiences.find_by_id(experience.id) is not None

    def test_should_return_404_when_repeated(
        self, postgres_database: PostgresDatabase
    ) -> None:
        goal = GoalFaker.fake()
        experience = SkillExperienceFaker.fake(goal_id=goal.id)
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add(experience)

        with _client(postgres_database.engine, goal.account_id) as client:
            first = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills/{experience.skill_id}',
                    headers=HEADERS,
                ),
            )
            repeated = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills/{experience.skill_id}',
                    headers=HEADERS,
                ),
            )

        assert first.status_code == 204
        assert repeated.status_code == 404

    def test_should_return_401_and_preserve_experience(
        self,
        postgres_database: PostgresDatabase,
        client: TestClient,
    ) -> None:
        goal = GoalFaker.fake()
        experience = SkillExperienceFaker.fake(goal_id=goal.id)
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add(experience)

        response = cast(
            'Response',
            client.delete(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{goal.id}/skills/{experience.skill_id}'
            ),
        )

        assert response.status_code == 401
        with database.transaction() as repositories:
            assert repositories.skill_experiences.find_by_id(experience.id) is not None

    def test_should_roll_back_when_transaction_fails(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        experience = SkillExperienceFaker.fake(goal_id=goal.id)
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add(experience)
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            AuthenticatedUser(
                account_id=goal.account_id,
                display_name='Pessoa Aprendente',
                time_zone=None,
            )
        )
        app.dependency_overrides[LearningPipe.get_database] = lambda: (
            _FailingCommitDatabase(database)
        )

        with TestClient(app, raise_server_exceptions=False) as client:
            response = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills/{experience.skill_id}',
                    headers=HEADERS,
                ),
            )

        assert response.status_code == 503
        with database.transaction() as repositories:
            assert repositories.skill_experiences.find_by_id(experience.id) is not None

    def test_should_complete_without_deadlock_behind_evaluation_lock_order(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        experience = SkillExperienceFaker.fake(goal_id=goal.id)
        attempt = ActivityAttemptFaker.fake(skill_experience_id=experience.id)
        evaluation = ActivityEvaluationFaker.fake(
            attempt_id=attempt.id,
            status=ActivityEvaluationStatus.PENDING,
        )
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add_many([experience])
            repositories.activity_attempts.add(attempt)
            repositories.activity_evaluations.add(evaluation)
        removal_started = Event()

        def remove() -> int:
            with _client(postgres_database.engine, goal.account_id) as client:
                removal_started.set()
                response = cast(
                    'Response',
                    client.delete(  # pyright: ignore[reportUnknownMemberType]
                        f'/learning/goals/{goal.id}/skills/{experience.skill_id}',
                        headers=HEADERS,
                    ),
                )
                return response.status_code

        with ThreadPoolExecutor(max_workers=1) as executor:
            with database.transaction() as repositories:
                locked = repositories.skill_experiences.find_by_id_for_update(
                    experience.id
                )
                assert locked is not None
                future = executor.submit(remove)
                assert removal_started.wait(timeout=5)
                locked_evaluation = (
                    repositories.activity_evaluations.find_by_attempt_id_for_update(
                        attempt.id
                    )
                )
                assert locked_evaluation is not None
            assert future.result(timeout=10) == 204

        with database.transaction() as repositories:
            assert repositories.skill_experiences.find_by_id(experience.id) is None
