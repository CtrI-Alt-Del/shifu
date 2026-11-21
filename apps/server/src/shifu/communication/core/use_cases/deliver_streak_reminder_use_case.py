import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar

from shifu.communication.core.domain.entities import (
    PushDelivery,
    PushSubscription,
    StreakReminder,
)
from shifu.communication.core.domain.enums import (
    PushDeliveryOutcomeKind,
    PushDeliveryStatus,
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
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


@dataclass(frozen=True, slots=True)
class _Target:
    delivery: PushDelivery
    subscription: PushSubscription


@dataclass(frozen=True, slots=True)
class _Reservation:
    reminder_id: str
    provider: PushNotificationProvider
    message: StreakReminderMessage
    ttl_seconds: int
    targets: tuple[_Target, ...]


class DeliverStreakReminderUseCase:
    """Send one daily reminder to every browser, at most once per browser.

    Each attempt reserves deliveries in one transaction, calls the push service
    outside any transaction and settles the outcomes in a final transaction. A
    delivery left ``SENDING`` by a crash is never sent again.
    """

    RETRY_DELAYS: ClassVar[tuple[timedelta, ...]] = (
        timedelta(minutes=1),
        timedelta(minutes=5),
        timedelta(minutes=15),
        timedelta(minutes=60),
    )
    IN_FLIGHT_GRACE: ClassVar[timedelta] = timedelta(minutes=2)
    UNCONFIGURED_CODE: ClassVar[str] = 'push_unconfigured'
    UNKNOWN_OUTCOME_CODE: ClassVar[str] = 'delivery_outcome_unknown'

    def __init__(
        self,
        database: CommunicationDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        push_notification_provider: PushNotificationProvider | None,
    ) -> None:
        self._database = database
        self._id_provider = id_provider
        self._clock_provider = clock_provider
        self._push_notification_provider = push_notification_provider

    def execute(self, reminder_id: str) -> StreakReminder | None:
        reservation = self._reserve(reminder_id)
        if not isinstance(reservation, _Reservation):
            return reservation

        outcomes = tuple(
            (
                target,
                reservation.provider.send(
                    reservation.message,
                    target.subscription,
                    ttl_seconds=reservation.ttl_seconds,
                ),
            )
            for target in reservation.targets
        )
        return self._settle(reservation.reminder_id, outcomes)

    def _reserve(self, reminder_id: str) -> _Reservation | StreakReminder | None:
        with self._database.transaction() as repositories:
            reminder = repositories.streak_reminders.find_by_id_for_update(reminder_id)
            if reminder is None:
                return None

            now = self._clock_provider.now()
            if self._finish_without_sending(repositories, reminder, now):
                return reminder

            subscriptions = repositories.push_subscriptions.find_many_by_account_id(
                reminder.account_id
            )
            deliveries = repositories.push_deliveries.find_many_by_reminder_id(
                reminder.id
            )
            if not subscriptions and not deliveries:
                reminder.skip(now)
                repositories.streak_reminders.update(reminder)
                return reminder

            attempted_ids = {delivery.subscription_id for delivery in deliveries}
            candidates = tuple(
                subscription
                for subscription in subscriptions
                if subscription.id not in attempted_ids
            )
            provider = self._push_notification_provider
            if provider is None:
                self._fail_unconfigured(repositories, reminder, candidates, now)
                return reminder

            targets = self._reserve_targets(repositories, reminder, candidates, now)
            if targets:
                reminder.start_attempt(now)
                repositories.streak_reminders.update(reminder)

            return _Reservation(
                reminder_id=reminder.id,
                provider=provider,
                message=StreakReminderMessage.for_streak(reminder.streak_days),
                ttl_seconds=max(
                    1, math.ceil((reminder.expires_at - now).total_seconds())
                ),
                targets=targets,
            )

    def _finish_without_sending(
        self,
        repositories: CommunicationDatabaseRepositories,
        reminder: StreakReminder,
        now: datetime,
    ) -> bool:
        """Return True when the attempt ends before any push is reserved."""

        if reminder.is_terminal:
            return True
        if reminder.next_attempt_at is not None and reminder.next_attempt_at > now:
            return True

        if now >= reminder.expires_at:
            reminder.expire(now)
        else:
            preference = repositories.streak_reminder_preferences.find_by_account_id(
                reminder.account_id
            )
            if preference is not None and preference.enabled:
                return False
            reminder.skip(now)

        repositories.streak_reminders.update(reminder)
        return True

    def _reserve_targets(
        self,
        repositories: CommunicationDatabaseRepositories,
        reminder: StreakReminder,
        candidates: tuple[PushSubscription, ...],
        now: datetime,
    ) -> tuple[_Target, ...]:
        targets: list[_Target] = []
        for subscription in candidates:
            delivery = self._new_delivery(reminder, subscription, now)
            if repositories.push_deliveries.try_add(delivery):
                targets.append(_Target(delivery, subscription))
        return tuple(targets)

    def _fail_unconfigured(
        self,
        repositories: CommunicationDatabaseRepositories,
        reminder: StreakReminder,
        candidates: tuple[PushSubscription, ...],
        now: datetime,
    ) -> None:
        for subscription in candidates:
            delivery = self._new_delivery(reminder, subscription, now)
            delivery.mark_failed(now, self.UNCONFIGURED_CODE)
            repositories.push_deliveries.try_add(delivery)
        reminder.mark_failed(now)
        repositories.streak_reminders.update(reminder)

    def _settle(
        self,
        reminder_id: str,
        outcomes: tuple[tuple[_Target, PushDeliveryOutcome], ...],
    ) -> StreakReminder | None:
        with self._database.transaction() as repositories:
            reminder = repositories.streak_reminders.find_by_id_for_update(reminder_id)
            if reminder is None:
                return None

            now = self._clock_provider.now()
            deliveries = {
                delivery.id: delivery
                for delivery in repositories.push_deliveries.find_many_by_reminder_id(
                    reminder.id
                )
            }
            subscriptions = {
                subscription.id: subscription
                for subscription in repositories.push_subscriptions.find_many_by_account_id(
                    reminder.account_id
                )
            }
            self._apply_outcomes(repositories, outcomes, deliveries, subscriptions, now)
            if reminder.is_terminal:
                return reminder

            in_flight = self._settle_stale_reservations(repositories, deliveries, now)
            self._conclude(reminder, deliveries, subscriptions, in_flight, now)
            repositories.streak_reminders.update(reminder)
            return reminder

    def _apply_outcomes(
        self,
        repositories: CommunicationDatabaseRepositories,
        outcomes: tuple[tuple[_Target, PushDeliveryOutcome], ...],
        deliveries: dict[str, PushDelivery],
        subscriptions: dict[str, PushSubscription],
        now: datetime,
    ) -> None:
        for target, outcome in outcomes:
            delivery = deliveries.get(target.delivery.id)
            if delivery is None or delivery.status is not PushDeliveryStatus.SENDING:
                continue
            match outcome.kind:
                case PushDeliveryOutcomeKind.ACCEPTED:
                    delivery.mark_sent(now)
                    repositories.push_deliveries.update(delivery)
                case PushDeliveryOutcomeKind.GONE:
                    delivery.mark_failed(now, outcome.code or 'subscription_gone')
                    repositories.push_deliveries.update(delivery)
                    repositories.push_subscriptions.remove(target.subscription)
                    subscriptions.pop(target.subscription.id, None)
                case PushDeliveryOutcomeKind.PERMANENT_FAILURE:
                    delivery.mark_failed(now, outcome.code or 'permanent_failure')
                    repositories.push_deliveries.update(delivery)
                case PushDeliveryOutcomeKind.TEMPORARY_FAILURE:
                    repositories.push_deliveries.remove(delivery)
                    del deliveries[delivery.id]

    def _settle_stale_reservations(
        self,
        repositories: CommunicationDatabaseRepositories,
        deliveries: dict[str, PushDelivery],
        now: datetime,
    ) -> bool:
        """Close reservations left by a crash; report whether one is still fresh."""

        in_flight = False
        for delivery in deliveries.values():
            if delivery.status is not PushDeliveryStatus.SENDING:
                continue
            if now - delivery.attempted_at >= self.IN_FLIGHT_GRACE:
                delivery.mark_failed(now, self.UNKNOWN_OUTCOME_CODE)
                repositories.push_deliveries.update(delivery)
            else:
                in_flight = True
        return in_flight

    def _conclude(
        self,
        reminder: StreakReminder,
        deliveries: dict[str, PushDelivery],
        subscriptions: dict[str, PushSubscription],
        in_flight: bool,
        now: datetime,
    ) -> None:
        attempted_ids = {delivery.subscription_id for delivery in deliveries.values()}
        accepted = any(
            delivery.status is PushDeliveryStatus.SENT
            for delivery in deliveries.values()
        )
        retry_needed = in_flight or any(
            subscription_id not in attempted_ids for subscription_id in subscriptions
        )

        if not retry_needed:
            if accepted:
                reminder.mark_sent(now)
            else:
                reminder.mark_failed(now)
            return

        next_attempt_at = now + self._retry_delay(reminder.attempt_count)
        if next_attempt_at < reminder.expires_at:
            reminder.schedule_retry(next_attempt_at, now)
        elif accepted:
            reminder.mark_sent(now)
        else:
            reminder.expire(now)

    def _new_delivery(
        self,
        reminder: StreakReminder,
        subscription: PushSubscription,
        now: datetime,
    ) -> PushDelivery:
        return PushDelivery.create(
            id=self._id_provider.generate(),
            reminder_id=reminder.id,
            subscription_id=subscription.id,
            attempted_at=now,
        )

    @classmethod
    def _retry_delay(cls, attempt_count: int) -> timedelta:
        index = min(max(attempt_count, 1), len(cls.RETRY_DELAYS)) - 1
        return cls.RETRY_DELAYS[index]
