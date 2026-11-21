from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.entities import (
    PushDelivery,
    StreakReminder,
    PushSubscription,
    StreakReminderPreference,
)
from shifu.communication.core.domain.enums import (
    PushDeliveryOutcomeKind,
    PushDeliveryStatus,
    StreakReminderStatus,
)
from shifu.communication.core.domain.structures import (
    PushDeliveryOutcome,
    StreakReminderMessage,
)
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
    PushNotificationProvider,
)
from shifu.communication.core.use_cases import DeliverStreakReminderUseCase
from shifu.fakers.communication.entities import (
    PushDeliveryFaker,
    PushSubscriptionFaker,
    StreakReminderFaker,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider

ACCEPTED = PushDeliveryOutcome(kind=PushDeliveryOutcomeKind.ACCEPTED)
GONE = PushDeliveryOutcome(kind=PushDeliveryOutcomeKind.GONE)
TEMPORARY = PushDeliveryOutcome(
    kind=PushDeliveryOutcomeKind.TEMPORARY_FAILURE,
    code='http_503',
)
PERMANENT = PushDeliveryOutcome(
    kind=PushDeliveryOutcomeKind.PERMANENT_FAILURE,
    code='http_413',
)


class TestDeliverStreakReminderUseCase:
    ACCOUNT_ID = '01JACCOUNT000000000000000001'
    REMINDER_ID = '01JREMINDER0000000000000001'
    NOW = datetime(2026, 11, 18, 21, 0, tzinfo=UTC)
    EXPIRES_AT = datetime(2026, 11, 19, 3, 0, tzinfo=UTC)

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.now = self.NOW
        self.in_transaction = False
        self.identifier_count = 0
        self.subscriptions: list[PushSubscription] = []
        self.deliveries: dict[str, PushDelivery] = {}
        self.outcomes: dict[str, PushDeliveryOutcome] = {}
        self.sent_to: list[str] = []
        self.reminder = StreakReminderFaker.fake(
            id=self.REMINDER_ID,
            account_id=self.ACCOUNT_ID,
            local_date=self.NOW.date(),
            streak_days=7,
            expires_at=self.EXPIRES_AT,
            created_at=self.NOW - timedelta(minutes=1),
        )
        self.preference: StreakReminderPreference | None = (
            StreakReminderPreference.create(
                account_id=self.ACCOUNT_ID,
                enabled=True,
                now=self.NOW,
            )
        )

        self.database = create_autospec(CommunicationDatabase, instance=True)
        self.repositories = create_autospec(
            CommunicationDatabaseRepositories,
            instance=True,
        )
        transaction = self.database.transaction.return_value
        transaction.__enter__.side_effect = self._enter_transaction
        transaction.__exit__.side_effect = self._exit_transaction
        self.repositories.streak_reminders.find_by_id_for_update.side_effect = (
            self._find_reminder
        )
        self.repositories.streak_reminder_preferences.find_by_account_id.side_effect = (
            self._find_preference
        )
        self.repositories.push_subscriptions.find_many_by_account_id.side_effect = (
            self._find_subscriptions
        )
        self.repositories.push_subscriptions.remove.side_effect = (
            self._remove_subscription
        )
        self.repositories.push_deliveries.find_many_by_reminder_id.side_effect = (
            self._find_deliveries
        )
        self.repositories.push_deliveries.try_add.side_effect = self._try_add_delivery
        self.repositories.push_deliveries.remove.side_effect = self._remove_delivery

        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.id_provider.generate.side_effect = self._generate_identifier
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.clock_provider.now.side_effect = lambda: self.now
        self.push_notification_provider = create_autospec(
            PushNotificationProvider,
            instance=True,
        )
        self.push_notification_provider.send.side_effect = self._send
        self.subject = DeliverStreakReminderUseCase(
            self.database,
            self.id_provider,
            self.clock_provider,
            self.push_notification_provider,
        )

    def _advance_to_next_attempt(self) -> None:
        assert self.reminder.next_attempt_at is not None
        self.now = self.reminder.next_attempt_at

    def _find_reminder(self, reminder_id: str) -> StreakReminder | None:
        return self.reminder if reminder_id == self.REMINDER_ID else None

    def _find_preference(self, _account_id: str) -> StreakReminderPreference | None:
        return self.preference

    def _find_subscriptions(self, _account_id: str) -> tuple[PushSubscription, ...]:
        return tuple(self.subscriptions)

    def _remove_subscription(self, subscription: PushSubscription) -> None:
        self.subscriptions.remove(subscription)

    def _find_deliveries(self, _reminder_id: str) -> tuple[PushDelivery, ...]:
        return tuple(self.deliveries.values())

    def _remove_delivery(self, delivery: PushDelivery) -> None:
        del self.deliveries[delivery.id]

    def _enter_transaction(self) -> CommunicationDatabaseRepositories:
        self.in_transaction = True
        return self.repositories

    def _exit_transaction(self, *_arguments: object) -> bool:
        self.in_transaction = False
        return False

    def _generate_identifier(self) -> str:
        self.identifier_count += 1
        return f'01JDELIVERY{self.identifier_count:015d}'

    def _try_add_delivery(self, delivery: PushDelivery) -> bool:
        if any(
            existing.subscription_id == delivery.subscription_id
            for existing in self.deliveries.values()
        ):
            return False
        self.deliveries[delivery.id] = delivery
        return True

    def _send(
        self,
        message: StreakReminderMessage,
        subscription: PushSubscription,
        *,
        ttl_seconds: int,
    ) -> PushDeliveryOutcome:
        assert not self.in_transaction
        self.sent_to.append(subscription.id)
        return self.outcomes[subscription.id]

    def _subscribe(
        self, subscription_id: str, outcome: PushDeliveryOutcome
    ) -> PushSubscription:
        subscription = PushSubscriptionFaker.fake(
            id=subscription_id,
            account_id=self.ACCOUNT_ID,
            created_at=self.NOW - timedelta(days=1),
        )
        self.subscriptions.append(subscription)
        self.outcomes[subscription_id] = outcome
        return subscription

    def _delivery_for(self, subscription_id: str) -> PushDelivery | None:
        return next(
            (
                delivery
                for delivery in self.deliveries.values()
                if delivery.subscription_id == subscription_id
            ),
            None,
        )

    def test_should_send_once_to_every_browser_and_mark_the_reminder_sent(
        self,
    ) -> None:
        self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)
        self._subscribe('01JSUBSCRIPTION00000000000002', ACCEPTED)

        result = self.subject.execute(self.REMINDER_ID)

        assert result is self.reminder
        assert self.reminder.status is StreakReminderStatus.SENT
        assert self.reminder.attempt_count == 1
        assert self.reminder.completed_at == self.NOW
        assert self.reminder.next_attempt_at is None
        assert sorted(self.sent_to) == [
            '01JSUBSCRIPTION00000000000001',
            '01JSUBSCRIPTION00000000000002',
        ]
        assert len(self.deliveries) == 2
        assert all(
            delivery.status is PushDeliveryStatus.SENT
            and delivery.completed_at == self.NOW
            for delivery in self.deliveries.values()
        )

    @pytest.mark.parametrize(
        ('streak_days', 'expected_body'),
        [
            (1, 'Sua sequência de 1 dia termina hoje — pratique para mantê-la'),
            (7, 'Sua sequência de 7 dias termina hoje — pratique para mantê-la'),
        ],
    )
    def test_should_send_the_message_with_the_streak_length(
        self, streak_days: int, expected_body: str
    ) -> None:
        self.reminder.streak_days = streak_days
        subscription = self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)

        self.subject.execute(self.REMINDER_ID)

        message = self.push_notification_provider.send.call_args.args[0]
        assert message == StreakReminderMessage(
            title='Shifu',
            body=expected_body,
            url='/',
            tag='shifu-streak-reminder',
        )
        assert self.push_notification_provider.send.call_args.args[1] == subscription

    def test_should_use_the_time_left_today_as_the_push_ttl(self) -> None:
        self.reminder.expires_at = self.NOW + timedelta(seconds=90, milliseconds=500)
        self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)

        self.subject.execute(self.REMINDER_ID)

        assert self.push_notification_provider.send.call_args.kwargs == {
            'ttl_seconds': 91
        }

    def test_should_remove_a_gone_browser_and_retry_only_the_temporary_one(
        self,
    ) -> None:
        accepted = self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)
        gone = self._subscribe('01JSUBSCRIPTION00000000000002', GONE)
        temporary = self._subscribe('01JSUBSCRIPTION00000000000003', TEMPORARY)

        first = self.subject.execute(self.REMINDER_ID)

        assert first is self.reminder
        assert self.reminder.status is StreakReminderStatus.PENDING
        assert self.reminder.attempt_count == 1
        assert self.reminder.next_attempt_at == self.NOW + timedelta(minutes=1)
        assert self.subscriptions == [accepted, temporary]
        self.repositories.push_subscriptions.remove.assert_called_once_with(gone)
        accepted_delivery = self._delivery_for(accepted.id)
        gone_delivery = self._delivery_for(gone.id)
        assert accepted_delivery is not None
        assert accepted_delivery.status is PushDeliveryStatus.SENT
        assert gone_delivery is not None
        assert gone_delivery.status is PushDeliveryStatus.FAILED
        assert gone_delivery.failure_code == 'subscription_gone'
        assert self._delivery_for(temporary.id) is None

        self.outcomes[temporary.id] = ACCEPTED
        self.sent_to.clear()
        self._advance_to_next_attempt()

        second = self.subject.execute(self.REMINDER_ID)

        assert second is self.reminder
        assert self.sent_to == [temporary.id]
        assert self.reminder.status is StreakReminderStatus.SENT
        assert self.reminder.attempt_count == 2
        temporary_delivery = self._delivery_for(temporary.id)
        assert temporary_delivery is not None
        assert temporary_delivery.status is PushDeliveryStatus.SENT
        self.repositories.push_subscriptions.remove.assert_called_once_with(gone)

    def test_should_follow_the_backoff_schedule_then_retry_hourly(self) -> None:
        self.reminder.expires_at = self.NOW + timedelta(hours=24)
        self._subscribe('01JSUBSCRIPTION00000000000001', TEMPORARY)
        expected_delays = [1, 5, 15, 60, 60, 60]

        for attempt, expected_minutes in enumerate(expected_delays, start=1):
            self.subject.execute(self.REMINDER_ID)

            assert self.reminder.status is StreakReminderStatus.PENDING
            assert self.reminder.attempt_count == attempt
            assert self.reminder.next_attempt_at == self.now + timedelta(
                minutes=expected_minutes
            )
            self._advance_to_next_attempt()

        assert len(self.sent_to) == len(expected_delays)

    def test_should_schedule_the_last_retry_that_still_fits_before_the_deadline(
        self,
    ) -> None:
        self.reminder.expires_at = self.NOW + timedelta(minutes=1, seconds=1)
        self._subscribe('01JSUBSCRIPTION00000000000001', TEMPORARY)

        self.subject.execute(self.REMINDER_ID)

        assert self.reminder.status is StreakReminderStatus.PENDING
        assert self.reminder.next_attempt_at == self.NOW + timedelta(minutes=1)

    def test_should_expire_when_no_retry_fits_before_the_deadline(self) -> None:
        self.reminder.expires_at = self.NOW + timedelta(minutes=1)
        self._subscribe('01JSUBSCRIPTION00000000000001', TEMPORARY)

        self.subject.execute(self.REMINDER_ID)

        assert self.reminder.status is StreakReminderStatus.EXPIRED
        assert self.reminder.next_attempt_at is None
        assert self.reminder.completed_at == self.NOW
        assert len(self.sent_to) == 1

    def test_should_not_send_anything_after_the_end_of_the_local_day(self) -> None:
        self.reminder.expires_at = self.NOW + timedelta(minutes=30)
        self._subscribe('01JSUBSCRIPTION00000000000001', TEMPORARY)
        self.subject.execute(self.REMINDER_ID)
        assert self.reminder.status is StreakReminderStatus.PENDING
        self.sent_to.clear()
        self.now = self.reminder.expires_at

        result = self.subject.execute(self.REMINDER_ID)

        assert result is self.reminder
        assert self.reminder.status is StreakReminderStatus.EXPIRED
        assert self.reminder.completed_at == self.reminder.expires_at
        assert self.sent_to == []

    def test_should_mark_the_reminder_sent_when_a_browser_accepted_and_no_retry_fits(
        self,
    ) -> None:
        self.reminder.expires_at = self.NOW + timedelta(minutes=1)
        self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)
        self._subscribe('01JSUBSCRIPTION00000000000002', TEMPORARY)

        self.subject.execute(self.REMINDER_ID)

        assert self.reminder.status is StreakReminderStatus.SENT

    def test_should_end_skipped_when_the_preference_is_turned_off_during_a_retry(
        self,
    ) -> None:
        self._subscribe('01JSUBSCRIPTION00000000000001', TEMPORARY)
        self.subject.execute(self.REMINDER_ID)
        assert self.reminder.status is StreakReminderStatus.PENDING
        self.sent_to.clear()
        assert self.preference is not None
        self.preference.change(enabled=False, now=self.now)
        self._advance_to_next_attempt()

        result = self.subject.execute(self.REMINDER_ID)

        assert result is self.reminder
        assert self.reminder.status is StreakReminderStatus.SKIPPED
        assert self.reminder.next_attempt_at is None
        assert self.sent_to == []

    def test_should_end_skipped_when_the_preference_was_never_set(self) -> None:
        self.preference = None
        self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)

        self.subject.execute(self.REMINDER_ID)

        assert self.reminder.status is StreakReminderStatus.SKIPPED
        self.push_notification_provider.send.assert_not_called()

    def test_should_end_skipped_when_there_is_no_browser_left(self) -> None:
        self.subject.execute(self.REMINDER_ID)

        assert self.reminder.status is StreakReminderStatus.SKIPPED
        self.push_notification_provider.send.assert_not_called()

    def test_should_not_retry_a_permanent_failure_and_keep_the_other_browsers(
        self,
    ) -> None:
        rejected = self._subscribe('01JSUBSCRIPTION00000000000001', PERMANENT)
        accepted = self._subscribe('01JSUBSCRIPTION00000000000002', ACCEPTED)

        self.subject.execute(self.REMINDER_ID)

        rejected_delivery = self._delivery_for(rejected.id)
        assert rejected_delivery is not None
        assert rejected_delivery.status is PushDeliveryStatus.FAILED
        assert rejected_delivery.failure_code == 'http_413'
        assert self.subscriptions == [rejected, accepted]
        assert self.reminder.status is StreakReminderStatus.SENT
        self.repositories.push_subscriptions.remove.assert_not_called()

    def test_should_mark_the_reminder_failed_when_every_browser_failed_permanently(
        self,
    ) -> None:
        self._subscribe('01JSUBSCRIPTION00000000000001', PERMANENT)

        self.subject.execute(self.REMINDER_ID)

        assert self.reminder.status is StreakReminderStatus.FAILED
        assert self.reminder.next_attempt_at is None
        assert self.reminder.completed_at == self.NOW
        assert len(self.sent_to) == 1

    def test_should_mark_the_reminder_failed_when_every_browser_is_gone(self) -> None:
        self._subscribe('01JSUBSCRIPTION00000000000001', GONE)

        self.subject.execute(self.REMINDER_ID)

        assert self.reminder.status is StreakReminderStatus.FAILED
        assert self.subscriptions == []

    def test_should_not_resend_to_a_browser_already_reserved_or_sent(self) -> None:
        sent = self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)
        failed = self._subscribe('01JSUBSCRIPTION00000000000002', ACCEPTED)
        fresh = self._subscribe('01JSUBSCRIPTION00000000000003', ACCEPTED)
        for subscription, status, code in (
            (sent, PushDeliveryStatus.SENT, None),
            (failed, PushDeliveryStatus.FAILED, 'http_413'),
        ):
            delivery = PushDeliveryFaker.fake(
                reminder_id=self.REMINDER_ID,
                subscription_id=subscription.id,
                status=status,
                attempted_at=self.NOW - timedelta(hours=1),
                completed_at=self.NOW - timedelta(hours=1),
                failure_code=code,
            )
            self.deliveries[delivery.id] = delivery

        self.subject.execute(self.REMINDER_ID)

        assert self.sent_to == [fresh.id]
        assert self.reminder.status is StreakReminderStatus.SENT

    def test_should_skip_a_browser_reserved_by_a_concurrent_attempt(self) -> None:
        subscription = self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)
        self.repositories.push_deliveries.try_add.side_effect = None
        self.repositories.push_deliveries.try_add.return_value = False

        result = self.subject.execute(self.REMINDER_ID)

        assert result is self.reminder
        assert subscription.id not in self.sent_to
        self.push_notification_provider.send.assert_not_called()
        assert self.reminder.attempt_count == 0

    def test_should_wait_for_a_recent_in_flight_reservation_without_resending(
        self,
    ) -> None:
        in_flight = self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)
        delivery = PushDeliveryFaker.fake(
            reminder_id=self.REMINDER_ID,
            subscription_id=in_flight.id,
            status=PushDeliveryStatus.SENDING,
            attempted_at=self.NOW - timedelta(seconds=10),
        )
        self.deliveries[delivery.id] = delivery

        self.subject.execute(self.REMINDER_ID)

        assert self.sent_to == []
        assert delivery.status is PushDeliveryStatus.SENDING
        assert self.reminder.status is StreakReminderStatus.PENDING
        assert self.reminder.next_attempt_at == self.NOW + timedelta(minutes=1)

    def test_should_settle_a_stale_reservation_as_unknown_without_resending(
        self,
    ) -> None:
        crashed = self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)
        delivery = PushDeliveryFaker.fake(
            reminder_id=self.REMINDER_ID,
            subscription_id=crashed.id,
            status=PushDeliveryStatus.SENDING,
            attempted_at=self.NOW - timedelta(minutes=10),
        )
        self.deliveries[delivery.id] = delivery

        self.subject.execute(self.REMINDER_ID)

        assert self.sent_to == []
        assert delivery.status is PushDeliveryStatus.FAILED
        assert delivery.failure_code == 'delivery_outcome_unknown'
        assert self.reminder.status is StreakReminderStatus.FAILED

    def test_should_send_to_a_browser_registered_while_the_reminder_was_retrying(
        self,
    ) -> None:
        first = self._subscribe('01JSUBSCRIPTION00000000000001', TEMPORARY)
        self.subject.execute(self.REMINDER_ID)
        self.sent_to.clear()
        late = self._subscribe('01JSUBSCRIPTION00000000000002', ACCEPTED)
        self.outcomes[first.id] = ACCEPTED
        self._advance_to_next_attempt()

        self.subject.execute(self.REMINDER_ID)

        assert sorted(self.sent_to) == [first.id, late.id]
        assert self.reminder.status is StreakReminderStatus.SENT

    def test_should_record_a_failure_when_push_is_not_configured(self) -> None:
        subscription = self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)
        subject = DeliverStreakReminderUseCase(
            self.database,
            self.id_provider,
            self.clock_provider,
            None,
        )

        result = subject.execute(self.REMINDER_ID)

        assert result is self.reminder
        assert self.reminder.status is StreakReminderStatus.FAILED
        delivery = self._delivery_for(subscription.id)
        assert delivery is not None
        assert delivery.status is PushDeliveryStatus.FAILED
        assert delivery.failure_code == 'push_unconfigured'
        assert self.sent_to == []

    def test_should_call_the_push_service_outside_any_transaction(self) -> None:
        self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)

        self.subject.execute(self.REMINDER_ID)

        self.push_notification_provider.send.assert_called_once()
        assert self.in_transaction is False

    @pytest.mark.parametrize(
        'status',
        [
            StreakReminderStatus.SENT,
            StreakReminderStatus.SKIPPED,
            StreakReminderStatus.EXPIRED,
            StreakReminderStatus.CANCELLED,
            StreakReminderStatus.FAILED,
        ],
    )
    def test_should_stop_without_sending_when_the_reminder_is_terminal(
        self, status: StreakReminderStatus
    ) -> None:
        self.reminder.status = status
        self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)

        result = self.subject.execute(self.REMINDER_ID)

        assert result is self.reminder
        assert self.reminder.status is status
        self.push_notification_provider.send.assert_not_called()
        self.repositories.streak_reminders.update.assert_not_called()
        self.repositories.push_deliveries.try_add.assert_not_called()

    def test_should_return_none_when_the_reminder_does_not_exist(self) -> None:
        result = self.subject.execute('01JMISSING000000000000000001')

        assert result is None
        self.push_notification_provider.send.assert_not_called()

    def test_should_wait_when_the_next_attempt_is_still_in_the_future(self) -> None:
        self.reminder.attempt_count = 1
        self.reminder.next_attempt_at = self.NOW + timedelta(minutes=5)
        self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)

        result = self.subject.execute(self.REMINDER_ID)

        assert result is self.reminder
        assert self.reminder.status is StreakReminderStatus.PENDING
        self.push_notification_provider.send.assert_not_called()

    def test_should_return_none_when_the_account_was_purged_during_the_send(
        self,
    ) -> None:
        self._subscribe('01JSUBSCRIPTION00000000000001', ACCEPTED)
        self.repositories.streak_reminders.find_by_id_for_update.side_effect = [
            self.reminder,
            None,
        ]

        result = self.subject.execute(self.REMINDER_ID)

        assert result is None
        self.repositories.push_deliveries.update.assert_not_called()
