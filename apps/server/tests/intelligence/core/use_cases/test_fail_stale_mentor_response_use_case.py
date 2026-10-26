from dataclasses import replace
from datetime import timedelta

import pytest
from shifu.intelligence.core.domain.enums import (
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.use_cases.fail_mentor_response_use_case import (
    FailMentorResponseUseCase,
)
from shifu.intelligence.core.use_cases.fail_stale_mentor_response_use_case import (
    FailStaleMentorResponseUseCase,
)
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
)


class TestFailStaleMentorResponseUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.repositories.mentor_response_attempts.find_current.return_value = (
            self.attempt
        )
        self.subject = FailStaleMentorResponseUseCase(
            self.database,
            FailMentorResponseUseCase(self.database, self.clock, self.access),
        )

    def test_should_fail_a_processing_attempt_whose_claim_expired(self) -> None:
        self.repositories.mentor_response_attempts.has_claim.return_value = False
        self.repositories.mentor_response_attempts.claim.return_value = True

        assert self.subject.execute('account', 'session') is True

        self.repositories.mentor_response_attempts.find_current.assert_any_call(
            'account', 'session'
        )
        self.repositories.mentor_response_attempts.claim.assert_called_once_with(
            'attempt',
            FailStaleMentorResponseUseCase.RECOVERY_OWNER,
            self.now,
            self.now + timedelta(minutes=5),
            'revision',
        )
        self.repositories.mentor_response_attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.PROCESSING,
            MentorResponseStatus.FAILED,
            'revision',
        )
        event = self.repositories.mentor_response_events.append.call_args.args[0]
        assert event.kind is MentorResponseEventKind.FAILED
        assert event.failure_code == 'service_unavailable'

    def test_should_keep_an_attempt_held_by_a_live_execution(self) -> None:
        self.repositories.mentor_response_attempts.has_claim.return_value = False
        self.repositories.mentor_response_attempts.claim.return_value = False

        assert self.subject.execute('account', 'session') is False

        self.repositories.mentor_response_attempts.transition.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()

    @pytest.mark.parametrize(
        'status',
        (
            MentorResponseStatus.QUEUED,
            MentorResponseStatus.COMPLETED,
            MentorResponseStatus.FAILED,
            MentorResponseStatus.CANCELLED,
        ),
    )
    def test_should_ignore_an_attempt_that_is_not_processing(
        self, status: MentorResponseStatus
    ) -> None:
        self.repositories.mentor_response_attempts.find_current.return_value = replace(
            self.attempt, status=status
        )

        assert self.subject.execute('account', 'session') is False

        self.repositories.mentor_response_attempts.claim.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_not_called()

    def test_should_ignore_a_session_without_attempts(self) -> None:
        self.repositories.mentor_response_attempts.find_current.return_value = None

        assert self.subject.execute('account', 'session') is False

        self.repositories.mentor_response_attempts.claim.assert_not_called()
