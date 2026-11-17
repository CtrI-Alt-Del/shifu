import logging
from dataclasses import replace
from decimal import Decimal
from unittest.mock import Mock, create_autospec

import pytest
from shifu.fakers.intelligence.entities import AiQuotaChargeFaker
from shifu.intelligence.core.domain.enums import (
    AiQuotaRequestKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    AiQuotaPolicy,
    MentorInferenceUsage,
)
from shifu.intelligence.core.interfaces import MentorTelemetryProvider
from shifu.intelligence.core.use_cases.record_mentor_inference_usage_use_case import (
    RecordMentorInferenceUsageUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.core.use_cases.ai_quota_test_setup import QUOTA_MONTH
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
)


class TestRecordMentorInferenceUsageUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.telemetry = create_autospec(MentorTelemetryProvider, instance=True)
        self.subject = RecordMentorInferenceUsageUseCase(
            self.database,
            self.clock,
            self.access,
            self.quota_policy,
            self.quota_calendar,
            self.telemetry,
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
        self.charge = AiQuotaChargeFaker.fake(
            request_kind=AiQuotaRequestKind.MENTOR_RESPONSE,
            request_id='attempt',
            account_id='account',
            month=QUOTA_MONTH,
        )
        self.quota_charges.find.return_value = self.charge
        self.quota_charges.find_for_update.return_value = self.charge

    def _subject_with(self, policy: AiQuotaPolicy) -> RecordMentorInferenceUsageUseCase:
        return RecordMentorInferenceUsageUseCase(
            self.database,
            self.clock,
            self.access,
            policy,
            self.quota_calendar,
            self.telemetry,
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

    def test_should_charge_the_journal_total_in_the_journal_transaction(self) -> None:
        effects = Mock()
        effects.attach_mock(
            self.repositories.mentor_response_attempts.journal_usage, 'journal'
        )
        effects.attach_mock(
            self.repositories.mentor_response_attempts.read_usage, 'read'
        )
        effects.attach_mock(self.quota_charges.find, 'find_charge')
        effects.attach_mock(self.quota_months.lock_existing, 'lock_month')
        effects.attach_mock(self.quota_charges.find_for_update, 'lock_charge')
        effects.attach_mock(self.quota_months.update, 'update_month')

        self.subject.execute('attempt', 'owner', self.usage)

        assert [entry[0] for entry in effects.mock_calls] == [
            'journal',
            'read',
            'find_charge',
            'lock_month',
            'lock_charge',
            'update_month',
        ]
        self.database.transaction.assert_called_once()
        self.quota_charges.find.assert_called_once_with(
            AiQuotaRequestKind.MENTOR_RESPONSE, 'attempt'
        )
        self.quota_months.lock_existing.assert_called_once_with('account', QUOTA_MONTH)
        assert self.charge.charged_units == 240
        assert self.quota_month.used_units == 240
        self.access.record_usage.assert_called_once()

    def test_should_charge_once_when_the_same_diary_is_reported_again(self) -> None:
        self.subject.execute('attempt', 'owner', self.usage)
        self.subject.execute('attempt', 'owner', self.usage)

        assert self.quota_month.used_units == 240
        self.quota_months.update.assert_called_once()
        self.quota_charges.update.assert_called_once()

    def test_should_charge_only_the_difference_when_the_diary_grows(self) -> None:
        second = MentorInferenceUsage(
            call_key='review:0',
            profile='review',
            used_tokens=60,
            input_tokens=50,
            output_tokens=10,
        )
        self.subject.execute('attempt', 'owner', self.usage)
        self.repositories.mentor_response_attempts.read_usage.return_value = (
            self.usage,
            second,
        )

        self.subject.execute('attempt', 'owner', second)

        assert self.charge.charged_units == 330
        assert self.quota_month.used_units == 330

    def test_should_round_the_request_total_up_once_not_per_call(self) -> None:
        policy = AiQuotaPolicy(
            monthly_limit_units=1000,
            input_weight=Decimal('0.4'),
            output_weight=Decimal('1.5'),
        )
        calls = (
            MentorInferenceUsage(
                call_key='writer:0',
                profile='writer',
                used_tokens=2,
                input_tokens=1,
                output_tokens=1,
            ),
            MentorInferenceUsage(
                call_key='writer:1',
                profile='writer',
                used_tokens=2,
                input_tokens=2,
                output_tokens=0,
            ),
        )
        self.repositories.mentor_response_attempts.read_usage.return_value = calls

        self._subject_with(policy).execute('attempt', 'owner', calls[1])

        # 0.4 + 1.5 + 0.8 + 0 = 2.7, rounded up once to 3 (never 2 + 1).
        assert self.charge.charged_units == 3
        assert self.quota_month.used_units == 3

    def test_should_charge_a_total_only_call_with_the_input_weight_and_warn(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        total_only = MentorInferenceUsage(
            call_key='writer:0', profile='writer', used_tokens=120
        )
        self.repositories.mentor_response_attempts.read_usage.return_value = (
            total_only,
        )

        with caplog.at_level(logging.WARNING):
            self.subject.execute('attempt', 'owner', total_only)

        assert self.charge.charged_units == 120
        assert self.quota_month.used_units == 120
        warnings = [
            r for r in caplog.records if 'ai_quota_total_only_usage' in r.message
        ]
        assert len(warnings) == 1
        assert 'mentor_response' in warnings[0].message
        assert 'attempt' in warnings[0].message

    def test_should_charge_zero_and_warn_for_a_call_without_counts(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        unknown = replace(
            self.usage, used_tokens=None, input_tokens=None, output_tokens=None
        )
        self.repositories.mentor_response_attempts.read_usage.return_value = (unknown,)

        with caplog.at_level(logging.WARNING):
            self.subject.execute('attempt', 'owner', unknown)

        assert self.charge.charged_units == 0
        assert self.quota_month.used_units == 0
        self.quota_months.update.assert_not_called()
        assert any('ai_quota_unknown_usage' in r.message for r in caplog.records)
        self.access.record_usage.assert_not_called()

    def test_should_charge_the_start_month_when_the_report_arrives_after_the_turn(
        self,
    ) -> None:
        self.quota_calendar.month_of.return_value = QUOTA_MONTH.replace(month=11)

        self.subject.execute('attempt', 'owner', self.usage)

        self.quota_months.lock_existing.assert_called_once_with('account', QUOTA_MONTH)
        self.quota_months.ensure_and_lock.assert_not_called()
        assert self.quota_month.used_units == 240

    def test_should_ignore_the_usage_of_a_refunded_attempt(self) -> None:
        self.charge.refund(self.now)

        self.subject.execute('attempt', 'owner', self.usage)

        assert self.charge.charged_units == 0
        assert self.quota_month.used_units == 0
        self.quota_months.update.assert_not_called()

    def test_should_ignore_the_usage_of_an_attempt_without_a_charge_row(self) -> None:
        self.quota_charges.find.return_value = None

        self.subject.execute('attempt', 'owner', self.usage)

        self.quota_months.lock_existing.assert_not_called()
        self.quota_months.update.assert_not_called()
        self.access.record_usage.assert_called_once()

    def test_should_not_charge_when_the_journal_rejects_the_call(self) -> None:
        self.repositories.mentor_response_attempts.journal_usage.return_value = False

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.usage)

        self.quota_charges.find.assert_not_called()
        self.quota_months.update.assert_not_called()

    def test_should_journal_and_charge_usage_reported_after_a_cancel(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id.return_value = replace(
            self.attempt, status=MentorResponseStatus.CANCELLED
        )

        self.subject.execute('attempt', 'owner', self.usage)

        self.repositories.mentor_response_attempts.journal_usage.assert_called_once_with(
            'attempt', 'owner', 'revision', self.usage
        )
        assert self.charge.charged_units == 240
        assert self.quota_month.used_units == 240
        self.quota_months.update.assert_called_once()
        usage = self.access.record_usage.call_args.args[1]
        assert usage.cancelled is True
        assert usage.used_tokens == 120

    def test_should_report_a_running_attempt_as_not_cancelled(self) -> None:
        self.subject.execute('attempt', 'owner', self.usage)

        assert self.access.record_usage.call_args.args[1].cancelled is False

    def test_should_still_require_the_execution_claim_after_a_cancel(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id.return_value = replace(
            self.attempt, status=MentorResponseStatus.CANCELLED
        )
        self.repositories.mentor_response_attempts.has_claim.return_value = False

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.usage)

        self.repositories.mentor_response_attempts.journal_usage.assert_not_called()
        self.quota_months.update.assert_not_called()

    @pytest.mark.parametrize(
        'status',
        [
            MentorResponseStatus.COMPLETED,
            MentorResponseStatus.FAILED,
            MentorResponseStatus.QUEUED,
        ],
    )
    def test_should_reject_and_not_journal_usage_of_a_settled_or_unstarted_attempt(
        self, status: MentorResponseStatus
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id.return_value = replace(
            self.attempt, status=status
        )

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.usage)

        self.repositories.mentor_response_attempts.journal_usage.assert_not_called()
        self.quota_charges.find.assert_not_called()
        self.quota_months.update.assert_not_called()
        self.access.record_usage.assert_not_called()

    def test_should_keep_a_refunded_charge_at_zero_for_late_usage_after_a_cancel(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id.return_value = replace(
            self.attempt, status=MentorResponseStatus.CANCELLED
        )
        self.charge.refund(self.now)

        self.subject.execute('attempt', 'owner', self.usage)

        assert self.charge.charged_units == 0
        assert self.quota_month.used_units == 0
        self.quota_months.update.assert_not_called()
