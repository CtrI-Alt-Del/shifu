from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from shifu.intelligence.core.domain.enums import (
    MentorActionKind,
    MentorActionProposalOutcome,
    MentorActionProposalStatus,
)
from shifu.intelligence.core.domain.structures import MentorActionCandidateGoal
from tests.fixtures.intelligence_fixture import OTHER_ACCOUNT

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.fixtures.intelligence_fixture import IntelligenceFixture


class TestGetMentorSessionController:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, mentor_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = mentor_client
        self.session_id, self.attempt_id, self.message_id = (
            intelligence_fixture.create_session(mentor_client)
        )
        self.path = f'/intelligence/mentor-sessions/{self.session_id}'

    def test_should_return_no_action_items_for_a_conversation_without_proposals(
        self,
    ) -> None:
        response = self.client.get(self.path)

        assert response.status_code == 200
        assert response.json()['action_items'] == []

    def test_should_return_every_proposal_with_its_current_state_and_survive_a_second_read(
        self,
    ) -> None:
        pending = self.fixture.seed_action_proposal(
            self.session_id, self.attempt_id, self.message_id
        )
        candidates = (
            MentorActionCandidateGoal(
                goal_id='goal-a',
                title='A',
                contains_skill=True,
                skill_experience_id='experience-a',
            ),
            MentorActionCandidateGoal(
                goal_id='goal-b',
                title='B',
                contains_skill=True,
                skill_experience_id='experience-b',
            ),
        )
        completed = self.fixture.seed_action_proposal(
            self.session_id,
            self.attempt_id,
            self.message_id,
            kind=MentorActionKind.REMOVE_SKILL,
            status=MentorActionProposalStatus.COMPLETED,
            outcome=MentorActionProposalOutcome.REMOVED,
            candidate_goals=candidates,
            goal_id=None,
            resolved_goal_id='goal-b',
            resolved_skill_experience_id='experience-b',
        )

        first = self.client.get(self.path)
        second = self.client.get(self.path)

        assert first.status_code == second.status_code == 200
        assert first.json()['action_items'] == second.json()['action_items']
        items = {item['id']: item for item in first.json()['action_items']}
        assert set(items) == {pending.id, completed.id}
        assert items[pending.id]['status'] == 'pending'
        assert items[pending.id]['kind'] == 'add_skill'
        assert items[pending.id]['source_message_id'] == self.message_id
        assert items[completed.id]['status'] == 'completed'
        assert items[completed.id]['outcome'] == 'removed'
        assert items[completed.id]['goal_id'] is None
        assert items[completed.id]['candidate_goals'] == [
            {
                'goal_id': 'goal-a',
                'title': 'A',
                'contains_skill': True,
                'skill_experience_id': 'experience-a',
            },
            {
                'goal_id': 'goal-b',
                'title': 'B',
                'contains_skill': True,
                'skill_experience_id': 'experience-b',
            },
        ]
        assert items[completed.id]['resolved_goal_id'] == 'goal-b'
        assert items[completed.id]['resolved_skill_experience_id'] == 'experience-b'

    def test_should_not_show_the_proposals_of_another_account(self) -> None:
        self.fixture.seed_action_proposal(
            self.session_id, self.attempt_id, self.message_id
        )

        with self.fixture.other_account_client() as other:
            response = other.get(self.path)

        assert response.status_code == 404

    def test_should_remove_the_proposals_with_the_deleted_conversation(self) -> None:
        self.fixture.seed_action_proposal(
            self.session_id, self.attempt_id, self.message_id
        )
        assert len(self.fixture.read_action_proposals(self.session_id)) == 1

        deleted = self.client.delete(self.path)

        assert deleted.status_code == 204
        assert self.fixture.read_action_proposals(self.session_id) == []
        assert self.client.get(self.path).status_code == 404

    def test_should_keep_the_proposals_of_other_conversations_when_one_is_deleted(
        self,
    ) -> None:
        other_session, other_attempt, other_message = self.fixture.create_session(
            self.client, '5b2d6f0e-2c68-4f7f-8c6e-0c9d0a9b3a11'
        )
        self.fixture.seed_action_proposal(
            self.session_id, self.attempt_id, self.message_id
        )
        kept = self.fixture.seed_action_proposal(
            other_session, other_attempt, other_message
        )

        assert self.client.delete(self.path).status_code == 204

        assert [
            item.id for item in self.fixture.read_action_proposals(other_session)
        ] == [kept.id]

    def test_should_remove_only_the_pending_proposals_of_a_cancelled_attempt(
        self,
    ) -> None:
        other_session, other_attempt, other_message = self.fixture.create_session(
            self.client, '5b2d6f0e-2c68-4f7f-8c6e-0c9d0a9b3a11'
        )
        pending = self.fixture.seed_action_proposal(
            self.session_id, self.attempt_id, self.message_id
        )
        declined = self.fixture.seed_action_proposal(
            self.session_id,
            self.attempt_id,
            self.message_id,
            status=MentorActionProposalStatus.DECLINED,
        )
        other_attempt_pending = self.fixture.seed_action_proposal(
            other_session, other_attempt, other_message
        )
        foreign = self.fixture.seed_action_proposal(
            self.session_id,
            self.attempt_id,
            self.message_id,
            account_id=OTHER_ACCOUNT.account_id,
        )

        cancelled = self.client.post(
            f'{self.path}/responses/{self.attempt_id}/cancel',
            json={'submission_key': '9a4e1c7b-6d23-4b58-8f10-3c5d7e9a1b22'},
        )

        assert cancelled.status_code == 200
        remaining = {
            item.id
            for item in (
                *self.fixture.read_action_proposals(self.session_id),
                *self.fixture.read_action_proposals(
                    self.session_id, OTHER_ACCOUNT.account_id
                ),
                *self.fixture.read_action_proposals(other_session),
            )
        }
        assert pending.id not in remaining
        assert remaining == {declined.id, other_attempt_pending.id, foreign.id}
