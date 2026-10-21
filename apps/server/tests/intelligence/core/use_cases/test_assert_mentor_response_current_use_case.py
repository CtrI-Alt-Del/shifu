from dataclasses import replace

import pytest
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.use_cases.assert_mentor_response_current_use_case import (
    AssertMentorResponseCurrentUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
)


class TestAssertMentorResponseCurrentUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.subject = AssertMentorResponseCurrentUseCase(
            self.database, self.clock, self.access
        )

    def test_should_accept_current_owned_processing_attempt(self) -> None:
        self.subject.execute('attempt', 'owner')

        self.repositories.mentor_response_attempts.has_claim.assert_called_once_with(
            'attempt', 'owner', self.now
        )
        self.access.assert_current.assert_called_once()

    def test_should_reject_missing_attempt_and_each_stale_current_condition(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id.return_value = None
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')

        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            self.attempt
        )
        stale_cases = (
            ('session', None),
            ('current', None),
            ('status', replace(self.attempt, status=MentorResponseStatus.CANCELLED)),
            ('revision', replace(self.attempt, access_revision='old-revision')),
            ('latest', replace(self.attempt, id='newer-attempt')),
            ('claim', False),
        )
        for case, value in stale_cases:
            self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
                self.session
            )
            self.repositories.mentor_response_attempts.find_by_id.side_effect = None
            self.repositories.mentor_response_attempts.find_by_id.return_value = (
                self.attempt
            )
            self.repositories.mentor_response_attempts.find_current.return_value = (
                self.attempt
            )
            self.repositories.mentor_response_attempts.has_claim.return_value = True
            if case == 'session':
                self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
                    value
                )
            elif case == 'current':
                self.repositories.mentor_response_attempts.find_by_id.side_effect = [
                    self.attempt,
                    value,
                ]
            elif case in ('status', 'revision'):
                self.repositories.mentor_response_attempts.find_by_id.side_effect = [
                    self.attempt,
                    value,
                ]
                self.repositories.mentor_response_attempts.find_by_id.return_value = (
                    value
                )
            elif case == 'latest':
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    value
                )
            else:
                self.repositories.mentor_response_attempts.has_claim.return_value = (
                    value
                )
            with pytest.raises(ServiceUnavailableError):
                self.subject.execute('attempt', 'owner')

    def test_should_fail_closed_when_access_is_revoked(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')
