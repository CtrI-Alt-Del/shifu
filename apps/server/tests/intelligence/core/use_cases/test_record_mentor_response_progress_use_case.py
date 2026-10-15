from dataclasses import replace
from typing import cast

import pytest

from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorWorkflowStep,
)
from shifu.intelligence.core.use_cases import RecordMentorResponseProgressUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorAccessGrant
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
)


class TestRecordMentorResponseProgressUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.subject = RecordMentorResponseProgressUseCase(
            self.database, self.clock, self.access
        )

    def test_should_append_the_current_workflow_step_as_progress(self) -> None:
        self.subject.execute('attempt', 'owner', MentorWorkflowStep.REVIEW_ANSWER)

        event = self.repositories.mentor_response_events.append.call_args.args[0]
        assert event.kind.value == 'status'
        assert event.status is MentorResponseStatus.PROCESSING
        assert event.progress is MentorWorkflowStep.REVIEW_ANSWER
        assert event.sequence == 2
        assert event.created_at == self.now
        self.repositories.mentor_response_attempts.has_claim.assert_called_once_with(
            'attempt', 'owner', self.now
        )
        self.access.assert_current.assert_called_once_with(
            MentorAccessGrant(
                account_id='account',
                access_revision='revision',
                operation_key='operation',
            )
        )

    @pytest.mark.parametrize(
        'step',
        ['write-answer', 'review-answer', None],
    )
    def test_should_reject_a_step_that_is_not_a_workflow_enum(
        self, step: object
    ) -> None:
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', cast('MentorWorkflowStep', step))

        self.database.transaction.assert_not_called()

    @pytest.mark.parametrize(
        'stale_state',
        [
            'missing_attempt',
            'not_processing',
            'missing_latest',
            'different_latest',
            'missing_claim',
        ],
    )
    def test_should_reject_progress_without_a_current_owned_processing_attempt(
        self, stale_state: str
    ) -> None:
        if stale_state == 'missing_attempt':
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None
        elif stale_state == 'not_processing':
            attempt = replace(self.attempt, status=MentorResponseStatus.QUEUED)
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = attempt
            self.repositories.mentor_response_attempts.find_current.return_value = (
                attempt
            )
        elif stale_state == 'missing_latest':
            self.repositories.mentor_response_attempts.find_current.return_value = None
        elif stale_state == 'different_latest':
            self.repositories.mentor_response_attempts.find_current.return_value = (
                replace(self.attempt, id='another-attempt')
            )
        else:
            self.repositories.mentor_response_attempts.has_claim.return_value = False

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', MentorWorkflowStep.WRITE_ANSWER)

        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_not_append_progress_after_access_is_revoked(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', MentorWorkflowStep.WRITE_ANSWER)

        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_response_events.next_sequence.assert_not_called()
