from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier

import pytest

from shifu.fakers.learning.entities import (
    ActivityAttemptFaker,
    ActivityEvaluationFaker,
    CompetencyProgressFaker,
    GoalFaker,
    SkillExperienceFaker,
)
from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    ActivityEvaluationStatus,
)
from shifu.learning.core.domain.structures import (
    AdaptiveConceptState,
    ConceptObservation,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from tests.fixtures.learning_mentor_action_fixture import (
    MentorActionFixture as Fixture,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture


def _path(goal_id: str) -> str:
    return f'/learning/goals/{goal_id}/mentor-skill-removals'


def _body(skill_experience_id: str, confirmation_id: str) -> dict[str, object]:
    return {
        'confirmation_id': confirmation_id,
        'skill_experience_id': skill_experience_id,
    }


class TestRemoveSkillExperienceFromMentorController:
    @pytest.fixture(autouse=True)
    def _setup(
        self,
        postgres_database: PostgresDatabase,
        redis_fixture: RedisFixture,
    ) -> None:
        self.engine = postgres_database.engine
        self.database = SqlalchemyLearningDatabase(self.engine)
        self.goal = GoalFaker.fake(account_id=Fixture.ACCOUNT_ID)
        self.other_goal = GoalFaker.fake(account_id=Fixture.ACCOUNT_ID)
        self.experience = SkillExperienceFaker.fake(goal_id=self.goal.id)
        self.sibling = SkillExperienceFaker.fake(goal_id=self.goal.id)
        self.same_skill_elsewhere = SkillExperienceFaker.fake(
            goal_id=self.other_goal.id,
            skill_id=self.experience.skill_id,
        )
        self.confirmation_id = Fixture.new_id()
        with self.database.transaction() as repositories:
            repositories.goals.add_many([self.goal, self.other_goal])
            repositories.skill_experiences.add_many(
                [self.experience, self.sibling, self.same_skill_elsewhere]
            )

    def _expected_body(self, **overrides: object) -> dict[str, object]:
        body: dict[str, object] = {
            'confirmationId': self.confirmation_id,
            'operation': 'remove_skill',
            'outcome': 'removed',
            'rejectionReason': None,
            'goalId': self.goal.id,
            'skillId': self.experience.skill_id,
            'skillExperienceId': self.experience.id,
        }
        return {**body, **overrides}

    def _seed_history(self) -> tuple[str, str]:
        progress = CompetencyProgressFaker.fake(skill_experience_id=self.experience.id)
        pending_attempt = ActivityAttemptFaker.fake(
            skill_experience_id=self.experience.id
        )
        failed_attempt = ActivityAttemptFaker.fake(
            skill_experience_id=self.experience.id
        )
        pending = ActivityEvaluationFaker.fake(
            attempt_id=pending_attempt.id,
            status=ActivityEvaluationStatus.PENDING,
        )
        failed = ActivityEvaluationFaker.fake(
            attempt_id=failed_attempt.id,
            status=ActivityEvaluationStatus.FAILED,
        )
        now = datetime(2026, 10, 23, tzinfo=UTC)
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
        with self.database.transaction() as repositories:
            repositories.competency_progresses.add(progress)
            repositories.activity_attempts.add_many([pending_attempt, failed_attempt])
            repositories.activity_evaluations.add_many([pending, failed])
            repositories.concept_observations.add_many(
                self.experience.id,
                pending_attempt.competency_id,
                (observation,),
            )
            repositories.concept_states.upsert_many(
                self.experience.id,
                {concept_id: pending_attempt.competency_id},
                (concept_state,),
                now,
            )
        return pending_attempt.id, failed_attempt.id

    def test_should_remove_the_experience_with_its_history_and_keep_everything_else(
        self,
    ) -> None:
        pending_attempt_id, failed_attempt_id = self._seed_history()

        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.experience.id, self.confirmation_id),
            )

        assert response.status_code == 200, response.text
        assert response.json() == self._expected_body()
        with self.database.transaction() as repositories:
            assert repositories.goals.find_by_id(self.goal.id) == self.goal
            assert repositories.skill_experiences.find_by_id(self.experience.id) is None
            assert (
                repositories.competency_progresses.find_many_by_skill_experience_id(
                    self.experience.id
                )
                == []
            )
            assert (
                repositories.activity_attempts.find_many_by_skill_experience_id(
                    self.experience.id
                )
                == []
            )
            assert (
                repositories.activity_evaluations.find_by_attempt_id(pending_attempt_id)
                is None
            )
            assert (
                repositories.activity_evaluations.find_by_attempt_id(failed_attempt_id)
                is None
            )
            assert (
                repositories.concept_observations.find_many_by_skill_experience_id(
                    self.experience.id
                )
                == []
            )
            assert (
                repositories.concept_states.find_many_by_skill_experience_id(
                    self.experience.id
                )
                == []
            )
            assert (
                repositories.skill_experiences.find_by_id(self.sibling.id) is not None
            )
            assert (
                repositories.skill_experiences.find_by_id(self.same_skill_elsewhere.id)
                is not None
            )
            assert repositories.goals.find_by_id(self.other_goal.id) == self.other_goal

    def test_should_keep_the_goal_when_the_removed_experience_was_the_last_one(
        self,
    ) -> None:
        with Fixture.client(self.engine) as client:
            first = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.experience.id, self.confirmation_id),
            )
            second = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.sibling.id, Fixture.new_id()),
            )

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert Fixture.count_experiences(self.engine, self.goal.id) == 0
        with self.database.transaction() as repositories:
            assert repositories.goals.find_by_id(self.goal.id) == self.goal
            assert (
                repositories.skill_experiences.find_by_id(self.same_skill_elsewhere.id)
                is not None
            )

    def test_should_store_one_receipt_and_one_outbox_event_on_first_resolution(
        self,
    ) -> None:
        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.experience.id, self.confirmation_id),
            )

        assert response.status_code == 200, response.text
        assert Fixture.count_receipts(self.engine) == 1
        with self.database.transaction() as repositories:
            receipt = repositories.mentor_action_receipts.find_by_confirmation_id(
                Fixture.ACCOUNT_ID, self.confirmation_id
            )
        assert receipt is not None
        assert receipt.skill_experience_id == self.experience.id
        events = Fixture.resolved_events(self.engine)
        assert len(events) == 1
        payload = events[0]
        resolved_at = payload.pop('resolved_at')
        assert isinstance(resolved_at, str)
        assert resolved_at.endswith('Z')
        assert payload == {
            'account_id': Fixture.ACCOUNT_ID,
            'confirmation_id': self.confirmation_id,
            'operation': 'remove_skill',
            'outcome': 'removed',
            'rejection_reason': None,
            'goal_id': self.goal.id,
            'skill_id': self.experience.skill_id,
            'skill_experience_id': self.experience.id,
        }

    def test_should_return_the_same_body_and_emit_nothing_when_repeated(self) -> None:
        request = _body(self.experience.id, self.confirmation_id)

        with Fixture.client(self.engine) as client:
            first = Fixture.post(client, _path(self.goal.id), request)
            repeated = Fixture.post(client, _path(self.goal.id), request)

        assert first.status_code == 200, first.text
        assert repeated.status_code == 200, repeated.text
        assert repeated.json() == first.json()
        assert Fixture.count_receipts(self.engine) == 1
        assert len(Fixture.resolved_events(self.engine)) == 1

    def test_should_reject_a_stale_confirmation_after_the_skill_was_added_again(
        self,
    ) -> None:
        with Fixture.client(self.engine) as client:
            first = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.experience.id, self.confirmation_id),
            )
            readded = SkillExperienceFaker.fake(
                goal_id=self.goal.id, skill_id=self.experience.skill_id
            )
            with self.database.transaction() as repositories:
                repositories.skill_experiences.add(readded)
            stale_confirmation_id = Fixture.new_id()
            stale = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.experience.id, stale_confirmation_id),
            )
            replayed = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.experience.id, self.confirmation_id),
            )

        assert first.json()['outcome'] == 'removed'
        assert stale.status_code == 200, stale.text
        assert stale.json() == self._expected_body(
            confirmationId=stale_confirmation_id,
            outcome='rejected',
            rejectionReason='experience_unavailable',
            skillId=None,
        )
        assert replayed.json() == first.json()
        with self.database.transaction() as repositories:
            assert repositories.skill_experiences.find_by_id(readded.id) is not None
        assert Fixture.count_receipts(self.engine) == 2
        assert len(Fixture.resolved_events(self.engine)) == 2

    @pytest.mark.parametrize('kind', ['missing', 'another-goal'])
    def test_should_reject_a_missing_or_mismatched_experience_without_effects(
        self,
        kind: str,
    ) -> None:
        other_goal_experience = SkillExperienceFaker.fake(goal_id=self.other_goal.id)
        with self.database.transaction() as repositories:
            repositories.skill_experiences.add(other_goal_experience)
        experience_id = (
            Fixture.new_id() if kind == 'missing' else other_goal_experience.id
        )
        before = Fixture.count_experiences(self.engine)

        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(experience_id, self.confirmation_id),
            )

        assert response.status_code == 200, response.text
        assert response.json() == self._expected_body(
            outcome='rejected',
            rejectionReason='experience_unavailable',
            skillId=None,
            skillExperienceId=experience_id,
        )
        assert Fixture.count_experiences(self.engine) == before
        assert Fixture.count_receipts(self.engine) == 1
        assert len(Fixture.resolved_events(self.engine)) == 1

    @pytest.mark.parametrize('goal_kind', ['foreign', 'missing'])
    def test_should_reject_a_foreign_or_missing_goal_as_unavailable_without_effects(
        self,
        goal_kind: str,
    ) -> None:
        goal_id = self.goal.id if goal_kind == 'foreign' else Fixture.new_id()

        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(goal_id),
                _body(self.experience.id, self.confirmation_id),
                Fixture.OTHER_HEADERS,
            )

        assert response.status_code == 200, response.text
        assert response.json() == self._expected_body(
            goalId=goal_id,
            outcome='rejected',
            rejectionReason='goal_unavailable',
            skillId=None,
        )
        with self.database.transaction() as repositories:
            assert (
                repositories.skill_experiences.find_by_id(self.experience.id)
                is not None
            )
        assert Fixture.count_receipts(self.engine) == 1

    @pytest.mark.parametrize('changed', ['experience', 'goal'])
    def test_should_return_409_for_a_divergent_payload_under_the_same_id(
        self,
        changed: str,
    ) -> None:
        request = _body(self.experience.id, self.confirmation_id)

        with Fixture.client(self.engine) as client:
            first = Fixture.post(client, _path(self.goal.id), request)
            conflict = (
                Fixture.post(
                    client,
                    _path(self.goal.id),
                    _body(self.sibling.id, self.confirmation_id),
                )
                if changed == 'experience'
                else Fixture.post(client, _path(self.other_goal.id), request)
            )

        assert first.status_code == 200, first.text
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()['code'] == 'conflict'
        with self.database.transaction() as repositories:
            assert (
                repositories.skill_experiences.find_by_id(self.sibling.id) is not None
            )
        assert Fixture.count_receipts(self.engine) == 1
        assert len(Fixture.resolved_events(self.engine)) == 1

    @pytest.mark.parametrize(
        'body',
        [
            {'skill_experience_id': 'EXPERIENCE'},
            {'confirmation_id': 'CONF'},
            {'confirmation_id': 'not-a-ulid', 'skill_experience_id': 'EXPERIENCE'},
            {'confirmation_id': 'CONF', 'skill_experience_id': 'not-a-ulid'},
            {
                'confirmation_id': 'CONF',
                'skill_experience_id': 'EXPERIENCE',
                'extra': 1,
            },
        ],
    )
    def test_should_return_422_for_an_invalid_body_without_effects(
        self,
        body: dict[str, object],
    ) -> None:
        resolved = {
            key: (
                self.confirmation_id
                if value == 'CONF'
                else self.experience.id
                if value == 'EXPERIENCE'
                else value
            )
            for key, value in body.items()
        }

        with Fixture.client(self.engine) as client:
            response = Fixture.post(client, _path(self.goal.id), resolved)

        assert response.status_code == 422, response.text
        assert Fixture.count_receipts(self.engine) == 0
        assert Fixture.count_experiences(self.engine) == 3

    @pytest.mark.parametrize('headers', [Fixture.INACTIVE_HEADERS, {}])
    def test_should_return_401_without_a_receipt_for_an_inactive_or_unauthenticated_account(
        self,
        headers: dict[str, str],
    ) -> None:
        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.experience.id, self.confirmation_id),
                headers,
            )

        assert response.status_code == 401, response.text
        assert Fixture.count_receipts(self.engine) == 0
        assert Fixture.count_experiences(self.engine) == 3
        assert Fixture.resolved_events(self.engine) == []

    def test_should_produce_one_removal_for_two_concurrent_identical_requests(
        self,
    ) -> None:
        request = _body(self.experience.id, self.confirmation_id)
        barrier = Barrier(2)

        def confirm() -> tuple[int, dict[str, object]]:
            with Fixture.client(self.engine) as client:
                barrier.wait(timeout=10)
                response = Fixture.post(client, _path(self.goal.id), request)
                return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(confirm) for _ in range(2)]
            results = [future.result(timeout=30) for future in futures]

        assert [status for status, _ in results] == [200, 200]
        assert results[0][1] == results[1][1]
        assert results[0][1]['outcome'] == 'removed'
        assert Fixture.count_experiences(self.engine) == 2
        assert Fixture.count_receipts(self.engine) == 1
        assert len(Fixture.resolved_events(self.engine)) == 1
