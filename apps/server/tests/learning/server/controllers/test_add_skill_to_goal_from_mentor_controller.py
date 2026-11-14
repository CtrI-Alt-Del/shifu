from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.fakers.curriculum.entities.skill_faker import SkillFaker
from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from tests.fixtures.learning_mentor_action_fixture import (
    MentorActionFixture as Fixture,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

_JUSTIFICATION = 'Você pediu ao Mentor para adicionar esta Habilidade.'


def _path(goal_id: str) -> str:
    return f'/learning/goals/{goal_id}/mentor-skill-additions'


def _body(
    skill_id: str,
    confirmation_id: str,
    justification: str = _JUSTIFICATION,
) -> dict[str, object]:
    return {
        'confirmation_id': confirmation_id,
        'skill_id': skill_id,
        'justification': justification,
    }


class TestAddSkillToGoalFromMentorController:
    @pytest.fixture(autouse=True)
    def _setup(
        self,
        postgres_database: PostgresDatabase,
        redis_fixture: RedisFixture,
    ) -> None:
        self.engine = postgres_database.engine
        self.database = SqlalchemyLearningDatabase(self.engine)
        self.goal = GoalFaker.fake(account_id=Fixture.ACCOUNT_ID)
        self.skill = SkillFaker.fake()
        self.confirmation_id = Fixture.new_id()
        with SqlalchemyCurriculumDatabase(self.engine).transaction() as repositories:
            repositories.skills.add_many([self.skill])
        with self.database.transaction() as repositories:
            repositories.goals.add(self.goal)

    def _expected_body(self, **overrides: object) -> dict[str, object]:
        body: dict[str, object] = {
            'confirmationId': self.confirmation_id,
            'operation': 'add_skill',
            'outcome': 'added',
            'rejectionReason': None,
            'goalId': self.goal.id,
            'skillId': self.skill.id,
            'skillExperienceId': None,
        }
        return {**body, **overrides}

    def test_should_add_a_not_started_experience_with_the_justification(self) -> None:
        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.skill.id, self.confirmation_id),
            )

        assert response.status_code == 200, response.text
        body = response.json()
        with self.database.transaction() as repositories:
            experiences = repositories.skill_experiences.find_many_by_goal_id(
                self.goal.id
            )
            assert len(experiences) == 1
            experience = experiences[0]
            assert experience.skill_id == self.skill.id
            assert experience.status is SkillExperienceStatus.NOT_STARTED
            assert experience.inclusion_reason == _JUSTIFICATION
            assert experience.diagnostic_run_id is None
            assert (
                repositories.competency_progresses.find_many_by_skill_experience_id(
                    experience.id
                )
                == []
            )
        assert body == self._expected_body(skillExperienceId=experience.id)

    def test_should_trim_the_justification_before_storing_it(self) -> None:
        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.skill.id, self.confirmation_id, f'  {_JUSTIFICATION}\n'),
            )

        assert response.status_code == 200, response.text
        with self.database.transaction() as repositories:
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                self.goal.id, self.skill.id
            )
        assert experience is not None
        assert experience.inclusion_reason == _JUSTIFICATION

    def test_should_store_one_receipt_and_one_outbox_event_on_first_resolution(
        self,
    ) -> None:
        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.skill.id, self.confirmation_id),
            )

        assert response.status_code == 200, response.text
        assert Fixture.count_receipts(self.engine) == 1
        with self.database.transaction() as repositories:
            receipt = repositories.mentor_action_receipts.find_by_confirmation_id(
                Fixture.ACCOUNT_ID, self.confirmation_id
            )
        assert receipt is not None
        assert receipt.goal_id == self.goal.id
        assert receipt.skill_id == self.skill.id
        assert receipt.skill_experience_id == response.json()['skillExperienceId']
        assert len(receipt.request_fingerprint) == 64
        events = Fixture.resolved_events(self.engine)
        assert len(events) == 1
        payload = events[0]
        resolved_at = payload.pop('resolved_at')
        assert isinstance(resolved_at, str)
        assert resolved_at.endswith('Z')
        assert payload == {
            'account_id': Fixture.ACCOUNT_ID,
            'confirmation_id': self.confirmation_id,
            'operation': 'add_skill',
            'outcome': 'added',
            'rejection_reason': None,
            'goal_id': self.goal.id,
            'skill_id': self.skill.id,
            'skill_experience_id': response.json()['skillExperienceId'],
        }

    def test_should_return_the_existing_experience_when_the_skill_is_present(
        self,
    ) -> None:
        existing = SkillExperienceFaker.fake(
            goal_id=self.goal.id,
            skill_id=self.skill.id,
            inclusion_reason='Motivo manual.',
        )
        with self.database.transaction() as repositories:
            repositories.skill_experiences.add(existing)

        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.skill.id, self.confirmation_id),
            )

        assert response.status_code == 200, response.text
        assert response.json() == self._expected_body(
            outcome='already_present', skillExperienceId=existing.id
        )
        assert Fixture.count_experiences(self.engine, self.goal.id) == 1
        with self.database.transaction() as repositories:
            stored = repositories.skill_experiences.find_by_id(existing.id)
        assert stored is not None
        assert stored.inclusion_reason == 'Motivo manual.'
        assert Fixture.count_receipts(self.engine) == 1
        assert len(Fixture.resolved_events(self.engine)) == 1

    def test_should_reject_a_foreign_goal_as_unavailable_without_effects(self) -> None:
        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.skill.id, self.confirmation_id),
                Fixture.OTHER_HEADERS,
            )

        assert response.status_code == 200, response.text
        assert response.json() == self._expected_body(
            outcome='rejected', rejectionReason='goal_unavailable'
        )
        assert Fixture.count_experiences(self.engine) == 0
        assert Fixture.count_receipts(self.engine) == 1
        events = Fixture.resolved_events(self.engine)
        assert [event['rejection_reason'] for event in events] == ['goal_unavailable']
        assert events[0]['account_id'] == Fixture.OTHER_ACCOUNT_ID

    def test_should_reject_a_missing_goal_exactly_like_a_foreign_goal(self) -> None:
        missing_goal_id = Fixture.new_id()

        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(missing_goal_id),
                _body(self.skill.id, self.confirmation_id),
            )

        assert response.status_code == 200, response.text
        assert response.json() == self._expected_body(
            outcome='rejected',
            rejectionReason='goal_unavailable',
            goalId=missing_goal_id,
        )
        assert Fixture.count_experiences(self.engine) == 0

    def test_should_reject_a_skill_missing_from_the_curriculum(self) -> None:
        missing_skill_id = Fixture.new_id()

        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(missing_skill_id, self.confirmation_id),
            )

        assert response.status_code == 200, response.text
        assert response.json() == self._expected_body(
            outcome='rejected',
            rejectionReason='skill_unavailable',
            skillId=missing_skill_id,
        )
        assert Fixture.count_experiences(self.engine) == 0
        assert Fixture.count_receipts(self.engine) == 1

    def test_should_return_the_same_body_and_emit_nothing_when_repeated(self) -> None:
        request = _body(self.skill.id, self.confirmation_id)

        with Fixture.client(self.engine) as client:
            first = Fixture.post(client, _path(self.goal.id), request)
            repeated = Fixture.post(client, _path(self.goal.id), request)

        assert first.status_code == 200, first.text
        assert repeated.status_code == 200, repeated.text
        assert repeated.json() == first.json()
        assert Fixture.count_experiences(self.engine, self.goal.id) == 1
        assert Fixture.count_receipts(self.engine) == 1
        assert len(Fixture.resolved_events(self.engine)) == 1

    def test_should_not_duplicate_the_addition_when_replayed_after_a_manual_removal(
        self,
    ) -> None:
        request = _body(self.skill.id, self.confirmation_id)

        with Fixture.client(self.engine) as client:
            first = Fixture.post(client, _path(self.goal.id), request)
            with self.database.transaction() as repositories:
                created = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                    self.goal.id, self.skill.id
                )
                assert created is not None
                repositories.skill_experiences.remove(created)
            repeated = Fixture.post(client, _path(self.goal.id), request)

        assert repeated.json() == first.json()
        assert Fixture.count_experiences(self.engine, self.goal.id) == 0
        assert len(Fixture.resolved_events(self.engine)) == 1

    @pytest.mark.parametrize(
        'changed',
        [
            {'justification': 'Outra justificativa.'},
            {'skill_id': None},
        ],
    )
    def test_should_return_409_for_a_divergent_payload_under_the_same_id(
        self,
        changed: dict[str, str | None],
    ) -> None:
        other_skill = SkillFaker.fake()
        with SqlalchemyCurriculumDatabase(self.engine).transaction() as repositories:
            repositories.skills.add_many([other_skill])
        request = _body(self.skill.id, self.confirmation_id)
        divergent = {
            **request,
            **{
                key: (other_skill.id if value is None else value)
                for key, value in changed.items()
            },
        }

        with Fixture.client(self.engine) as client:
            first = Fixture.post(client, _path(self.goal.id), request)
            conflict = Fixture.post(client, _path(self.goal.id), divergent)

        assert first.status_code == 200, first.text
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()['code'] == 'conflict'
        assert (
            conflict.json()['message']
            == 'Esta confirmação já foi usada com outros dados.'
        )
        assert Fixture.count_experiences(self.engine, self.goal.id) == 1
        assert Fixture.count_receipts(self.engine) == 1
        assert len(Fixture.resolved_events(self.engine)) == 1

    def test_should_return_409_for_the_same_id_naming_another_goal(self) -> None:
        other_goal = GoalFaker.fake(account_id=Fixture.ACCOUNT_ID)
        with self.database.transaction() as repositories:
            repositories.goals.add(other_goal)
        request = _body(self.skill.id, self.confirmation_id)

        with Fixture.client(self.engine) as client:
            first = Fixture.post(client, _path(self.goal.id), request)
            conflict = Fixture.post(client, _path(other_goal.id), request)

        assert first.status_code == 200, first.text
        assert conflict.status_code == 409, conflict.text
        assert Fixture.count_experiences(self.engine, other_goal.id) == 0
        assert Fixture.count_receipts(self.engine) == 1

    @pytest.mark.parametrize(
        'body',
        [
            {'skill_id': 'SKILL', 'justification': 'Motivo.'},
            {'confirmation_id': 'CONF', 'justification': 'Motivo.'},
            {'confirmation_id': 'CONF', 'skill_id': 'SKILL'},
            {
                'confirmation_id': 'not-a-ulid',
                'skill_id': 'SKILL',
                'justification': 'Motivo.',
            },
            {
                'confirmation_id': 'CONF',
                'skill_id': 'not-a-ulid',
                'justification': 'Motivo.',
            },
            {'confirmation_id': 'CONF', 'skill_id': 'SKILL', 'justification': '   '},
            {
                'confirmation_id': 'CONF',
                'skill_id': 'SKILL',
                'justification': 'x' * 2001,
            },
            {
                'confirmation_id': 'CONF',
                'skill_id': 'SKILL',
                'justification': 'Motivo.',
                'extra': 1,
            },
        ],
    )
    def test_should_return_422_for_an_invalid_body_without_a_receipt(
        self,
        body: dict[str, object],
    ) -> None:
        resolved = {
            key: (
                self.confirmation_id
                if value == 'CONF'
                else self.skill.id
                if value == 'SKILL'
                else value
            )
            for key, value in body.items()
        }

        with Fixture.client(self.engine) as client:
            response = Fixture.post(client, _path(self.goal.id), resolved)

        assert response.status_code == 422, response.text
        assert Fixture.count_receipts(self.engine) == 0
        assert Fixture.count_experiences(self.engine) == 0

    def test_should_return_422_for_an_invalid_goal_id(self) -> None:
        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path('not-a-ulid'),
                _body(self.skill.id, self.confirmation_id),
            )

        assert response.status_code == 422, response.text
        assert Fixture.count_receipts(self.engine) == 0

    @pytest.mark.parametrize('headers', [Fixture.INACTIVE_HEADERS, {}])
    def test_should_return_401_without_a_receipt_for_an_inactive_or_unauthenticated_account(
        self,
        headers: dict[str, str],
    ) -> None:
        with Fixture.client(self.engine) as client:
            response = Fixture.post(
                client,
                _path(self.goal.id),
                _body(self.skill.id, self.confirmation_id),
                headers,
            )

        assert response.status_code == 401, response.text
        assert Fixture.count_receipts(self.engine) == 0
        assert Fixture.count_experiences(self.engine) == 0
        assert Fixture.resolved_events(self.engine) == []

    def test_should_produce_one_effect_for_two_concurrent_identical_requests(
        self,
    ) -> None:
        request = _body(self.skill.id, self.confirmation_id)
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
        assert results[0][1]['outcome'] == 'added'
        assert Fixture.count_experiences(self.engine, self.goal.id) == 1
        assert Fixture.count_receipts(self.engine) == 1
        assert len(Fixture.resolved_events(self.engine)) == 1

    def test_should_produce_one_receipt_for_two_concurrent_requests_to_a_missing_goal(
        self,
    ) -> None:
        missing_goal_id = Fixture.new_id()
        request = _body(self.skill.id, self.confirmation_id)
        barrier = Barrier(2)

        def confirm() -> tuple[int, dict[str, object]]:
            with Fixture.client(self.engine) as client:
                barrier.wait(timeout=10)
                response = Fixture.post(client, _path(missing_goal_id), request)
                return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(confirm) for _ in range(2)]
            results = [future.result(timeout=30) for future in futures]

        assert [status for status, _ in results] == [200, 200]
        assert results[0][1] == results[1][1]
        assert results[0][1]['rejectionReason'] == 'goal_unavailable'
        assert Fixture.count_receipts(self.engine) == 1
        assert len(Fixture.resolved_events(self.engine)) == 1
