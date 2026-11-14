from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from shifu.intelligence.core.domain.enums import (
    MentorActionProposalOutcome,
    MentorActionProposalRejectionReason,
    MentorActionProposalStatus,
)
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.shared.core.domain.errors import AuthorizationError
from tests.fixtures.intelligence_fixture import (
    IntelligenceFixture,
    configure_mentor_access,
    iso,
)

if TYPE_CHECKING:
    from shifu.intelligence.core.domain.entities import MentorActionProposal

_ACTION_ITEM_KEYS = {
    'id',
    'source_message_id',
    'kind',
    'skill_id',
    'skill_name',
    'goal_id',
    'goal_title',
    'skill_experience_id',
    'candidate_goals',
    'justification',
    'status',
    'outcome',
    'rejection_reason',
    'resolved_goal_id',
    'resolved_skill_experience_id',
    'created_at',
}
_UNKNOWN_ID = '0' * 25 + '1'


def _path(session_id: str, proposal_id: str) -> str:
    return f'/intelligence/mentor-sessions/{session_id}/action-proposals/{proposal_id}/decline'


class TestDeclineMentorActionProposalController:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, mentor_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = mentor_client
        self.session_id, self.attempt_id, self.message_id = (
            intelligence_fixture.create_session(mentor_client)
        )
        self.proposal = intelligence_fixture.seed_action_proposal(
            self.session_id, self.attempt_id, self.message_id
        )

    def _stored(self) -> MentorActionProposal:
        [stored] = self.fixture.read_action_proposals(self.session_id)
        return stored

    def test_should_decline_a_pending_proposal_and_return_the_item(self) -> None:
        response = self.client.post(_path(self.session_id, self.proposal.id))

        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        body = response.json()
        assert set(body) == _ACTION_ITEM_KEYS
        assert body['id'] == self.proposal.id
        assert body['source_message_id'] == self.message_id
        assert body['kind'] == 'add_skill'
        assert body['status'] == 'declined'
        assert body['outcome'] is None
        assert body['rejection_reason'] is None
        assert body['candidate_goals'] == []
        assert body['justification'] == self.proposal.justification
        assert body['created_at'] == iso(self.proposal.created_at)
        stored = self._stored()
        assert stored.status is MentorActionProposalStatus.DECLINED
        assert stored.outcome is None

    def test_should_keep_the_card_declined_after_reloading_the_conversation(
        self,
    ) -> None:
        self.client.post(_path(self.session_id, self.proposal.id))

        detail = self.client.get(f'/intelligence/mentor-sessions/{self.session_id}')

        assert detail.status_code == 200
        [item] = detail.json()['action_items']
        assert item['id'] == self.proposal.id
        assert item['status'] == 'declined'

    def test_should_refuse_declining_twice(self) -> None:
        assert (
            self.client.post(_path(self.session_id, self.proposal.id)).status_code
            == 200
        )

        response = self.client.post(_path(self.session_id, self.proposal.id))

        assert response.status_code == 409
        assert response.json() == {
            'code': 'conflict',
            'message': 'Esta ação já foi concluída.',
        }
        assert self._stored().status is MentorActionProposalStatus.DECLINED

    @pytest.mark.parametrize(
        ('status', 'outcome', 'reason'),
        [
            (
                MentorActionProposalStatus.COMPLETED,
                MentorActionProposalOutcome.ADDED,
                None,
            ),
            (
                MentorActionProposalStatus.REJECTED,
                None,
                MentorActionProposalRejectionReason.SKILL_UNAVAILABLE,
            ),
        ],
    )
    def test_should_refuse_declining_a_proposal_that_already_has_an_outcome(
        self,
        status: MentorActionProposalStatus,
        outcome: MentorActionProposalOutcome | None,
        reason: MentorActionProposalRejectionReason | None,
    ) -> None:
        resolved = self.fixture.seed_action_proposal(
            self.session_id,
            self.attempt_id,
            self.message_id,
            status=status,
            outcome=outcome,
            rejection_reason=reason,
            resolved_goal_id='goal',
        )

        response = self.client.post(_path(self.session_id, resolved.id))

        assert response.status_code == 409
        stored = {
            item.id: item
            for item in self.fixture.read_action_proposals(self.session_id)
        }
        assert stored[resolved.id].status is status
        assert stored[resolved.id].outcome is outcome

    def test_should_hide_an_unknown_proposal(self) -> None:
        response = self.client.post(_path(self.session_id, _UNKNOWN_ID))

        assert response.status_code == 404
        assert self._stored().status is MentorActionProposalStatus.PENDING

    def test_should_hide_an_unknown_conversation(self) -> None:
        response = self.client.post(_path(_UNKNOWN_ID, self.proposal.id))

        assert response.status_code == 404
        assert self._stored().status is MentorActionProposalStatus.PENDING

    def test_should_hide_a_proposal_that_belongs_to_another_account(self) -> None:
        with self.fixture.other_account_client() as other:
            response = other.post(_path(self.session_id, self.proposal.id))

            assert response.status_code == 404
            other_session, _, _ = self.fixture.create_session(
                other, '0f7d1b6e-9d6b-4d8b-9e57-1f3a5c1e2d44'
            )
            assert other.post(_path(other_session, self.proposal.id)).status_code == 404
        assert self._stored().status is MentorActionProposalStatus.PENDING

    def test_should_hide_a_proposal_of_another_conversation_of_the_owner(self) -> None:
        other_session, _, _ = self.fixture.create_session(
            self.client, '5b2d6f0e-2c68-4f7f-8c6e-0c9d0a9b3a11'
        )

        response = self.client.post(_path(other_session, self.proposal.id))

        assert response.status_code == 404
        assert self._stored().status is MentorActionProposalStatus.PENDING

    def test_should_reject_a_malformed_identifier_through_request_validation(
        self,
    ) -> None:
        response = self.client.post(_path(self.session_id, 'not-a-ulid'))

        assert response.status_code == 422
        assert self._stored().status is MentorActionProposalStatus.PENDING

    def test_should_reject_the_decline_when_the_access_revision_changed(self) -> None:
        app = self.fixture.mentor_app()
        access = configure_mentor_access(app)
        access.assert_current.side_effect = AuthorizationError()

        with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
            response = client.post(_path(self.session_id, self.proposal.id))

        assert response.status_code == 403
        assert self._stored().status is MentorActionProposalStatus.PENDING

    def test_should_not_expose_the_proposal_to_another_account_in_its_events(
        self,
    ) -> None:
        with self.fixture.other_account_client() as other:
            response = other.get(
                f'/intelligence/mentor-sessions/{self.session_id}/events'
            )

        assert response.status_code == 404

    def test_should_replay_the_action_event_with_the_current_state_of_the_proposal(
        self,
    ) -> None:
        # The event was stored while the proposal was pending; the replay must show
        # the state at read time. A completed event status ends the stream.
        proposal = self.fixture.seed_action_proposal(
            self.session_id,
            self.attempt_id,
            self.message_id,
            event_status=MentorResponseStatus.COMPLETED,
        )
        events_path = f'/intelligence/mentor-sessions/{self.session_id}/events'

        def action_state() -> dict[str, object]:
            response = self.client.get(events_path, params={'after_sequence': 1})
            assert response.status_code == 200
            data = [
                line.removeprefix('data:')
                for line in response.text.splitlines()
                if line.startswith('data:')
            ]
            payload = json.loads(data[-1])
            assert payload['kind'] == 'action'
            assert payload['block'] is None
            return payload['action_proposal']

        assert action_state()['status'] == 'pending'
        assert self.client.post(_path(self.session_id, proposal.id)).status_code == 200

        replayed = action_state()
        assert replayed['id'] == proposal.id
        assert replayed['status'] == 'declined'
