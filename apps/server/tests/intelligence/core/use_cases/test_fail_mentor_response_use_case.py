from dataclasses import replace
from datetime import timedelta
from unittest.mock import Mock

import pytest
from shifu.fakers.intelligence.entities import AiQuotaChargeFaker
from shifu.intelligence.core.domain.enums import (
    AiQuotaRequestKind,
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.use_cases.fail_mentor_response_use_case import (
    FailMentorResponseUseCase,
)
from tests.intelligence.core.use_cases.ai_quota_test_setup import QUOTA_MONTH
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
)


class TestFailMentorResponseUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.subject = FailMentorResponseUseCase(
            self.database,
            self.clock,
            self.access,
            self.quota_policy,
            self.quota_calendar,
        )
        self.charge = AiQuotaChargeFaker.fake(
            request_kind=AiQuotaRequestKind.MENTOR_RESPONSE,
            request_id='attempt',
            account_id='account',
            month=QUOTA_MONTH,
            charged_units=300,
        )
        self.quota_month.used_units = 500
        self.quota_charges.find.return_value = self.charge
        self.quota_charges.find_for_update.return_value = self.charge

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

    def test_should_refund_the_charged_units_in_the_transaction_that_writes_failed(
        self,
    ) -> None:
        effects = Mock()
        effects.attach_mock(
            self.repositories.mentor_response_attempts.transition, 'failed'
        )
        effects.attach_mock(self.quota_charges.find, 'find_charge')
        effects.attach_mock(self.quota_months.lock_existing, 'lock_month')
        effects.attach_mock(self.quota_charges.find_for_update, 'lock_charge')
        effects.attach_mock(self.quota_months.update, 'update_month')
        effects.attach_mock(self.quota_charges.update, 'update_charge')
        effects.attach_mock(self.repositories.mentor_response_events.append, 'event')

        assert (
            self.subject.execute('attempt', 'owner', 'service_unavailable')
            is MentorResponseStatus.FAILED
        )

        assert [entry[0] for entry in effects.mock_calls] == [
            'failed',
            'find_charge',
            'lock_month',
            'lock_charge',
            'update_month',
            'update_charge',
            'event',
        ]
        self.database.transaction.assert_called_once()
        self.quota_months.lock_existing.assert_called_once_with('account', QUOTA_MONTH)
        assert self.quota_month.used_units == 200
        assert self.charge.refunded is True

    def test_should_refund_nothing_twice_when_the_failure_is_repeated(self) -> None:
        self.subject.execute('attempt', 'owner', 'service_unavailable')
        self.subject.execute('attempt', 'owner', 'service_unavailable')

        assert self.quota_month.used_units == 200
        self.quota_months.update.assert_called_once()

    def test_should_refund_to_the_starting_month_after_the_calendar_turned(
        self,
    ) -> None:
        self.quota_calendar.month_of.return_value = QUOTA_MONTH.replace(month=11)

        self.subject.execute('attempt', 'owner', 'service_unavailable')

        self.quota_months.lock_existing.assert_called_once_with('account', QUOTA_MONTH)
        assert self.quota_month.used_units == 200

    def test_should_mark_a_request_without_usage_as_refunded_without_changing_the_month(
        self,
    ) -> None:
        self.charge.charged_units = 0
        self.quota_month.used_units = 500

        self.subject.execute('attempt', 'owner', 'service_unavailable')

        assert self.charge.refunded is True
        assert self.quota_month.used_units == 500

    def test_should_not_refund_when_the_failure_transition_is_lost(self) -> None:
        self.repositories.mentor_response_attempts.transition.return_value = False

        self.subject.execute('attempt', 'owner', 'service_unavailable')

        self.quota_charges.find.assert_not_called()
        self.quota_months.update.assert_not_called()
        assert self.charge.refunded is False

    @pytest.mark.parametrize(
        'status',
        (
            MentorResponseStatus.COMPLETED,
            MentorResponseStatus.CANCELLED,
            MentorResponseStatus.FAILED,
        ),
    )
    def test_should_keep_the_charge_of_an_attempt_that_is_not_failing(
        self, status: MentorResponseStatus
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, status=status
        )

        self.subject.execute('attempt', 'owner', 'service_unavailable')

        self.quota_charges.find.assert_not_called()
        self.quota_months.update.assert_not_called()
        assert self.quota_month.used_units == 500

    def test_should_refund_even_when_the_attempt_access_is_stale(self) -> None:
        from shifu.shared.core.domain.errors import ServiceUnavailableError

        self.access.assert_current.side_effect = ServiceUnavailableError()

        self.subject.execute('attempt', 'owner', 'service_unavailable')

        assert self.quota_month.used_units == 200
        assert self.charge.refunded is True

    def test_should_not_recreate_a_purged_month_while_refunding(self) -> None:
        self.quota_months.lock_existing.return_value = None

        assert (
            self.subject.execute('attempt', 'owner', 'service_unavailable')
            is MentorResponseStatus.FAILED
        )

        self.quota_months.ensure_and_lock.assert_not_called()
        self.quota_charges.find_for_update.assert_not_called()
        self.quota_months.update.assert_not_called()
