from dataclasses import replace
from datetime import timedelta

import pytest
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.use_cases.renew_mentor_response_claim_use_case import (
    RenewMentorResponseClaimUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
)


class TestRenewMentorResponseClaimUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.subject = RenewMentorResponseClaimUseCase(
            self.database, self.clock, self.access
        )

    def test_should_renew_only_the_current_claim_for_five_minutes(self) -> None:
        assert self.subject.execute('attempt', 'owner') is True

        self.repositories.mentor_response_attempts.renew_claim.assert_called_once_with(
            'attempt', 'owner', self.now, self.now + timedelta(minutes=5), 'revision'
        )
        self.access.assert_current.assert_called()

    def test_should_return_false_for_missing_or_stale_attempt(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id.return_value = None
        assert self.subject.execute('missing', 'owner') is False
        self.access.assert_current.assert_not_called()

        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            self.attempt
        )
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, status=MentorResponseStatus.CANCELLED
        )
        assert self.subject.execute('attempt', 'owner') is False
        self.repositories.mentor_response_attempts.renew_claim.assert_not_called()

        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = self.attempt
        self.repositories.mentor_response_attempts.find_current.return_value = replace(
            self.attempt, id='newer-attempt'
        )
        assert self.subject.execute('attempt', 'owner') is False

    def test_should_return_false_when_claim_renewal_is_rejected(self) -> None:
        self.repositories.mentor_response_attempts.renew_claim.return_value = False

        assert self.subject.execute('attempt', 'owner') is False

    def test_should_fail_closed_when_access_changes_before_or_after_renewal(
        self,
    ) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')
        self.repositories.mentor_response_attempts.renew_claim.assert_not_called()

        self.access.assert_current.side_effect = [None, ServiceUnavailableError()]
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')
        self.repositories.mentor_response_attempts.renew_claim.assert_called_once()
