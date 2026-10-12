import pytest
from shifu.intelligence.core.domain.errors import (
    MentorInputInvalidError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.use_cases import ReadMentorResponseEventsUseCase
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
