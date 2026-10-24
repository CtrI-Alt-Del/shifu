import pytest
from shifu.fakers.intelligence.entities import MentorActionProposalFaker
from shifu.intelligence.core.domain.enums import (
    MentorActionProposalStatus,
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.errors import (
    MentorInputInvalidError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.domain.structures import MentorResponseEvent
from shifu.intelligence.core.use_cases import ReadMentorResponseEventsUseCase
from shifu.intelligence.core.use_cases.mentor_detail import mentor_action_item
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.core.use_cases.mentor_response_test_setup import (
    MentorResponseTestSetup,
)


class TestReadMentorResponseEventsUseCase(MentorResponseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare()
        self.subject = ReadMentorResponseEventsUseCase(self.database, self.access)

    def test_should_replay_after_cursor_without_generation(self) -> None:
        self.repositories.mentor_response_events.find_after.return_value = ()
        assert self.subject.execute('account', 'session', 42) == ()
        self.repositories.mentor_response_events.find_after.assert_called_once_with(
            'account', 'session', 42
        )
        self.repositories.mentor_sessions.find_by_id_for_update.assert_called_once_with(
            'account', 'session'
        )
        self.access.authorize.assert_called_once_with('account', 'read:session')
        self.access.assert_current.assert_called_once_with(
            self.access.authorize.return_value
        )
        self.repositories.events.add.assert_not_called()

    def test_should_replay_action_events_with_the_current_proposal_state(self) -> None:
        proposal = MentorActionProposalFaker.fake(
            id='proposal',
            session_id='session',
            learner_message_id='message',
            status=MentorActionProposalStatus.DECLINED,
        )
        item = mentor_action_item(proposal)
        action_event = MentorResponseEvent(
            session_id='session',
            attempt_id='attempt',
            sequence=3,
            kind=MentorResponseEventKind.ACTION,
            status=MentorResponseStatus.PROCESSING,
            block=None,
            consultation=None,
            failure_code=None,
            created_at=self.now,
            action_proposal=item,
        )
        self.repositories.mentor_response_events.find_after.return_value = (
            action_event,
        )

        events = self.subject.execute('account', 'session', 2)

        assert events == (action_event,)
        assert events[0].block is None
        assert events[0].action_proposal is not None
        assert events[0].action_proposal.status is MentorActionProposalStatus.DECLINED
        assert events[0].action_proposal == item

    def test_should_reject_negative_cursor_without_read(self) -> None:
        with pytest.raises(MentorInputInvalidError):
            self.subject.execute('account', 'session', -1)
        self.database.transaction.assert_not_called()

    def test_should_hide_foreign_resource(self) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None
        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'foreign', 0)
        self.repositories.mentor_response_events.find_after.assert_not_called()

    def test_should_stop_replay_after_revocation(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'session', 0)
        self.repositories.mentor_response_events.find_after.assert_not_called()
