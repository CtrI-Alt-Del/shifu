from dataclasses import replace
from unittest.mock import create_autospec

import pytest
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.domain.structures import MentorInferenceUsage
from shifu.intelligence.core.interfaces import MentorTelemetryProvider
from shifu.intelligence.core.use_cases.record_mentor_inference_usage_use_case import (
    RecordMentorInferenceUsageUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
)


class TestRecordMentorInferenceUsageUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.telemetry = create_autospec(MentorTelemetryProvider, instance=True)
        self.subject = RecordMentorInferenceUsageUseCase(
            self.database, self.clock, self.access, self.telemetry
        )
        self.usage = MentorInferenceUsage(
            call_key='generated-0:writer:0',
            profile='writer',
            used_tokens=120,
            input_tokens=80,
            output_tokens=40,
            cost_usd=0.01,
        )
        self.repositories.mentor_response_attempts.journal_usage.return_value = True
        self.repositories.mentor_response_attempts.read_usage.return_value = (
            self.usage,
        )

    def test_should_journal_once_and_report_aggregate_usage(self) -> None:
        self.subject.execute('attempt', 'owner', self.usage)

        self.repositories.mentor_response_attempts.journal_usage.assert_called_once_with(
            'attempt', 'owner', 'revision', self.usage
        )
        self.telemetry.record_inference.assert_called_once_with(
            'writer', 120, 80, 40, 0.01
        )
        grant = self.access.record_usage.call_args.args[0]
        usage = self.access.record_usage.call_args.args[1]
        assert grant.account_id == 'account'
        assert grant.access_revision == 'revision'
        assert grant.operation_key == 'operation'
        assert usage.attempt_id == 'attempt'
        assert usage.used_tokens == 120
        assert usage.cancelled is False

    def test_should_skip_aggregate_when_token_usage_is_unknown(self) -> None:
        unknown = replace(self.usage, used_tokens=None)
        self.repositories.mentor_response_attempts.read_usage.return_value = (unknown,)

        self.subject.execute('attempt', 'owner', unknown)

        self.telemetry.record_inference.assert_called_once()
        self.access.record_usage.assert_not_called()

    def test_should_fail_closed_if_usage_journal_is_unavailable(self) -> None:
        self.repositories.mentor_response_attempts.read_usage.return_value = None

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.usage)

        self.access.record_usage.assert_not_called()

    @pytest.mark.parametrize(
        'usage',
        (
            MentorInferenceUsage(call_key='Bad key', profile='writer', used_tokens=1),
            MentorInferenceUsage(call_key='call', profile='  ', used_tokens=1),
            MentorInferenceUsage(call_key='call', profile='writer', used_tokens=-1),
            MentorInferenceUsage(
                call_key='call',
                profile='writer',
                used_tokens=True,  # type: ignore[arg-type]
            ),
            MentorInferenceUsage(
                call_key='call', profile='writer', used_tokens=1, input_tokens=-1
            ),
            MentorInferenceUsage(
                call_key='call',
                profile='writer',
                used_tokens=1,
                input_tokens=2,
                output_tokens=2,
            ),
            MentorInferenceUsage(
                call_key='call', profile='writer', used_tokens=1, cost_usd=float('nan')
            ),
            MentorInferenceUsage(
                call_key='call', profile='writer', used_tokens=1, cost_usd=-0.1
            ),
        ),
    )
    def test_should_reject_malformed_usage_before_repository_or_telemetry(
        self, usage: MentorInferenceUsage
    ) -> None:
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', usage)

        self.database.transaction.assert_not_called()
        self.telemetry.record_inference.assert_not_called()

    def test_should_require_active_attempt_and_owned_execution_claim(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id.return_value = None
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('missing', 'owner', self.usage)

        self.repositories.mentor_response_attempts.find_by_id.return_value = replace(
            self.attempt, status=MentorResponseStatus.CANCELLED
        )
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.usage)

        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            self.attempt
        )
        self.repositories.mentor_response_attempts.has_claim.return_value = False
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.usage)

        self.repositories.mentor_response_attempts.journal_usage.assert_not_called()

    def test_should_fail_closed_when_journal_or_access_provider_rejects(self) -> None:
        self.repositories.mentor_response_attempts.journal_usage.return_value = False
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.usage)
        self.telemetry.record_inference.assert_not_called()

        self.repositories.mentor_response_attempts.journal_usage.return_value = True
        self.access.assert_current.side_effect = ServiceUnavailableError()
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.usage)
        self.telemetry.record_inference.assert_not_called()

    def test_should_not_let_telemetry_failure_block_usage_recording(self) -> None:
        self.telemetry.record_inference.side_effect = RuntimeError(
            'private provider data'
        )

        self.subject.execute('attempt', 'owner', self.usage)

        self.access.record_usage.assert_called_once()
