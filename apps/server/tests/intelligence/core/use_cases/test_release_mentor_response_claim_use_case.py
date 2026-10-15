import pytest
from shifu.intelligence.core.use_cases.release_mentor_response_claim_use_case import (
    ReleaseMentorResponseClaimUseCase,
)
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
)


class TestReleaseMentorResponseClaimUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.subject = ReleaseMentorResponseClaimUseCase(self.database)

    def test_should_release_only_the_supplied_execution_owner(self) -> None:
        self.subject.execute('attempt', 'owner')

        self.repositories.mentor_response_attempts.release_claim.assert_called_once_with(
            'attempt', 'owner'
        )
