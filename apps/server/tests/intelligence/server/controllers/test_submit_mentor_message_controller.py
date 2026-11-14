from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from shifu.intelligence.core.domain.enums import MentorActionProposalStatus

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.fixtures.intelligence_fixture import IntelligenceFixture

_PENDING_ERROR = {
    'code': 'conflict',
    'message': 'Confirme ou recuse a ação proposta para continuar.',
}
_FIRST_KEY = '8d2b7c4e-4a1f-4c3e-9b52-6f1d3a7e9c01'
_SECOND_KEY = '3f9e2a1d-7b6c-4d85-8e40-2a5c9b1f7d02'


class TestSubmitMentorMessageController:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, mentor_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = mentor_client
        self.session_id, self.attempt_id, self.message_id = (
            intelligence_fixture.create_session(mentor_client)
        )
        intelligence_fixture.complete_response(
            self.session_id, self.attempt_id, self.message_id
        )
        self.path = f'/intelligence/mentor-sessions/{self.session_id}/messages'

    def _propose(self) -> str:
        return self.fixture.seed_action_proposal(
            self.session_id, self.attempt_id, self.message_id
        ).id

    def _decline(self, proposal_id: str) -> int:
        return self.client.post(
            f'/intelligence/mentor-sessions/{self.session_id}'
            f'/action-proposals/{proposal_id}/decline'
        ).status_code

    def _submit(self, key: str, content: str = 'sim') -> int:
        return self.client.post(
            self.path,
            json={'submission_key': key, 'content': content, 'context_hint': None},
        ).status_code

    def _message_count(self) -> int:
        detail = self.client.get(f'/intelligence/mentor-sessions/{self.session_id}')
        return len(detail.json()['messages']['items'])

    def test_should_refuse_a_new_message_while_a_proposal_is_pending(self) -> None:
        self._propose()
        before = self._message_count()

        response = self.client.post(
            self.path,
            json={'submission_key': _FIRST_KEY, 'content': 'sim', 'context_hint': None},
        )

        assert response.status_code == 409
        assert response.json() == _PENDING_ERROR
        assert self._message_count() == before
        [stored] = self.fixture.read_action_proposals(self.session_id)
        assert stored.status is MentorActionProposalStatus.PENDING

    def test_should_accept_the_message_after_the_proposal_is_declined(self) -> None:
        proposal_id = self._propose()
        assert self._submit(_FIRST_KEY) == 409

        assert self._decline(proposal_id) == 200

        assert self._submit(_FIRST_KEY) == 202

    def test_should_return_the_action_items_in_the_submission_detail(self) -> None:
        proposal_id = self._propose()
        assert self._decline(proposal_id) == 200

        response = self.client.post(
            self.path,
            json={
                'submission_key': _FIRST_KEY,
                'content': 'Obrigado',
                'context_hint': None,
            },
        )

        assert response.status_code == 202
        [item] = response.json()['action_items']
        assert item['id'] == proposal_id
        assert item['status'] == 'declined'

    def test_should_replay_an_earlier_submission_even_while_a_proposal_is_pending(
        self,
    ) -> None:
        # The first key was accepted before the proposal existed.
        accepted = self.client.post(
            self.path,
            json={
                'submission_key': _FIRST_KEY,
                'content': 'Obrigado',
                'context_hint': None,
            },
        )
        assert accepted.status_code == 202
        body = accepted.json()
        attempt_id = body['response']['attempt_id']
        message_id = body['pending_learner_message_id']
        self.fixture.complete_response(self.session_id, attempt_id, message_id)
        self.fixture.seed_action_proposal(self.session_id, attempt_id, message_id)

        replay = self._submit(_FIRST_KEY, 'Obrigado')
        new_submission = self._submit(_SECOND_KEY, 'sim')

        assert replay == 200
        assert new_submission == 409
