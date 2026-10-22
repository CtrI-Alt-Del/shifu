from dataclasses import replace

import pytest
from shifu.intelligence.core.domain.enums import (
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.use_cases.publish_mentor_response_block_use_case import (
    PublishMentorResponseBlockUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
    context_snapshot,
)


class TestPublishMentorResponseBlockUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.subject = PublishMentorResponseBlockUseCase(
            self.database, self.clock, self.access, self.context_provider
        )

    def test_should_publish_approved_block_as_sequenced_event(self) -> None:
        assert self.subject.execute('attempt', 'owner', self.block, self.context)

        event = self.repositories.mentor_response_events.append.call_args.args[0]
        assert event.kind is MentorResponseEventKind.BLOCK
        assert event.status is MentorResponseStatus.PROCESSING
        assert event.sequence == 2
        assert event.block == self.block
        assert event.consultation is None
        assert event.failure_code is None

    def test_should_treat_a_previously_published_block_key_as_idempotent(self) -> None:
        persisted = replace(self.block, content='Persisted authoritative answer')
        self.repositories.mentor_response_events.snapshot.return_value = replace(
            self.snapshot, blocks=(persisted,)
        )

        assert self.subject.execute('attempt', 'owner', self.block, self.context)

        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_response_events.next_sequence.assert_not_called()

    def test_should_hide_missing_attempt_without_reading_context(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id.return_value = None

        assert (
            self.subject.execute('missing', 'owner', self.block, self.context) is False
        )

        self.context_provider.read.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_reject_changed_permissions_and_revoked_access(self) -> None:
        self.context_provider.read.return_value = context_snapshot(
            eligible_references=('new-reference',)
        )
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.block, self.context)
        self.repositories.mentor_response_events.append.assert_not_called()

        self.context_provider.read.return_value = self.context
        self.access.assert_current.side_effect = ServiceUnavailableError()
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.block, self.context)
        self.repositories.mentor_response_events.append.assert_not_called()

    @pytest.mark.parametrize(
        'failure',
        (
            'missing-session',
            'missing-attempt',
            'not-processing',
            'stale-revision',
            'not-latest',
            'claim',
        ),
    )
    def test_should_not_publish_without_a_current_owned_processing_claim(
        self, failure: str
    ) -> None:
        if failure == 'missing-session':
            self.repositories.mentor_sessions.find_by_id_for_update.return_value = None
        elif failure == 'missing-attempt':
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None
        elif failure == 'not-processing':
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
                self.attempt, status=MentorResponseStatus.CANCELLED
            )
        elif failure == 'stale-revision':
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
                self.attempt, access_revision='old-revision'
            )
        elif failure == 'not-latest':
            self.repositories.mentor_response_attempts.find_current.return_value = (
                replace(self.attempt, id='newer-attempt')
            )
        else:
            self.repositories.mentor_response_attempts.has_claim.return_value = False

        assert (
            self.subject.execute('attempt', 'owner', self.block, self.context) is False
        )

        self.repositories.mentor_response_events.append.assert_not_called()
