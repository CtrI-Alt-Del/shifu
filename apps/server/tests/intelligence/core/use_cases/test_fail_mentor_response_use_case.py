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
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
)


class TestFailMentorResponseUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.subject = FailMentorResponseUseCase(self.database, self.clock, self.access)

    def test_should_fail_current_attempt_and_emit_only_safe_generic_event(self) -> None:
        assert (
            self.subject.execute('attempt', 'owner', 'service_unavailable')
            is MentorResponseStatus.FAILED
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
        assert event.block is None
        assert event.consultation is None

    def test_should_remove_the_pending_proposal_of_the_failed_attempt(self) -> None:
        self.subject.execute('attempt', 'owner', 'service_unavailable')

        self.repositories.mentor_action_proposals.remove_pending_by_attempt_id.assert_called_once_with(
            'account', 'attempt'
        )

    def test_should_keep_proposals_when_the_failure_transition_is_lost(self) -> None:
        self.repositories.mentor_response_attempts.transition.return_value = False

        self.subject.execute('attempt', 'owner', 'service_unavailable')

        self.repositories.mentor_action_proposals.remove_pending_by_attempt_id.assert_not_called()

    def test_should_recover_an_expired_claim_before_failure(self) -> None:
        self.repositories.mentor_response_attempts.has_claim.return_value = False
        self.repositories.mentor_response_attempts.claim.return_value = True

        assert (
            self.subject.execute('attempt', 'new-owner', 'service_unavailable')
            is MentorResponseStatus.FAILED
        )

        self.repositories.mentor_response_attempts.claim.assert_called_once_with(
            'attempt',
            'new-owner',
            self.now,
            self.now + timedelta(minutes=5),
            'revision',
        )

    @pytest.mark.parametrize('failure_code', ('provider_error', '', None, []))
    def test_should_reject_unapproved_failure_codes(self, failure_code: object) -> None:
        with pytest.raises(ValueError):
            self.subject.execute('attempt', 'owner', failure_code)  # type: ignore[arg-type]

        self.database.transaction.assert_not_called()

    def test_should_return_safely_for_missing_or_terminal_attempt(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None
        assert (
            self.subject.execute('missing', 'owner', 'service_unavailable')
            is MentorResponseStatus.CANCELLED
        )

        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = self.attempt
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None
        assert (
            self.subject.execute('attempt', 'owner', 'service_unavailable')
            is MentorResponseStatus.CANCELLED
        )

        self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
            self.session
        )
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, status=MentorResponseStatus.COMPLETED
        )
        assert (
            self.subject.execute('attempt', 'owner', 'service_unavailable')
            is MentorResponseStatus.COMPLETED
        )

    def test_should_not_fail_when_attempt_is_no_longer_latest_or_claim_is_owned_elsewhere(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_current.return_value = replace(
            self.attempt, id='newer-attempt'
        )
        assert (
            self.subject.execute('attempt', 'owner', 'service_unavailable')
            is MentorResponseStatus.CANCELLED
        )

        self.repositories.mentor_response_attempts.find_current.return_value = (
            self.attempt
        )
        self.repositories.mentor_response_attempts.has_claim.return_value = False
        self.repositories.mentor_response_attempts.claim.return_value = False
        assert (
            self.subject.execute('attempt', 'owner', 'service_unavailable')
            is MentorResponseStatus.PROCESSING
        )
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_return_current_status_if_terminal_transition_loses_race(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.transition.return_value = False

        assert (
            self.subject.execute('attempt', 'owner', 'service_unavailable')
            is MentorResponseStatus.PROCESSING
        )
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_emit_the_terminal_event_when_the_attempt_access_is_stale(
        self,
    ) -> None:
        from shifu.shared.core.domain.errors import ServiceUnavailableError

        self.access.assert_current.side_effect = ServiceUnavailableError()

        assert (
            self.subject.execute('attempt', 'owner', 'service_unavailable')
            is MentorResponseStatus.FAILED
        )
        event = self.repositories.mentor_response_events.append.call_args.args[0]
        assert event.kind is MentorResponseEventKind.FAILED
        assert event.status is MentorResponseStatus.FAILED
        assert event.failure_code == 'service_unavailable'
