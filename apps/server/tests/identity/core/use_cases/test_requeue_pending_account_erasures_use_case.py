from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec
from uuid import uuid4

import pytest

from shifu.identity.core.domain.events import (
    AccountErasureOperationalAlertRequestedEvent,
    AccountErasureRequestedEvent,
)
from shifu.identity.core.domain.structures import AccountErasureOverdueParticipant
from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases import RequeuePendingAccountErasuresUseCase
from shifu.shared.core.interfaces import ClockProvider


class TestRequeuePendingAccountErasuresUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.now = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.erasure_id = uuid4()
        self.closed_at = self.now - timedelta(hours=25)
        self.due_at = self.closed_at + timedelta(hours=24)
        self.repositories.account_erasures.find_pending.return_value = [self.erasure_id]
        self.repositories.account_erasures.find_overdue_pending_participants.return_value = [
            AccountErasureOverdueParticipant(
                erasure_id=self.erasure_id,
                module='learning',
                closed_at=self.closed_at,
                due_at=self.due_at,
            )
        ]
        self.subject = RequeuePendingAccountErasuresUseCase(
            self.database,
            self.clock,
        )

    def test_should_requeue_cleanup_and_emit_stable_sanitized_overdue_incident(
        self,
    ) -> None:
        assert self.subject.execute() == 1

        events = [call.args[0] for call in self.repositories.events.add.call_args_list]
        assert len(events) == 2
        assert isinstance(events[0], AccountErasureRequestedEvent)
        assert isinstance(events[1], AccountErasureOperationalAlertRequestedEvent)
        alert = events[1].payload
        assert alert.erasure_id == str(self.erasure_id)
        assert alert.module == 'learning'
        assert alert.failure_code == 'erasure_deadline_exceeded'
        assert alert.closed_at == self.closed_at
        assert alert.due_at == self.due_at
        assert alert.incident_id
        assert not hasattr(alert, 'account_id')
        assert not hasattr(alert, 'email')
        self.repositories.account_erasures.find_overdue_pending_participants.assert_called_once_with(
            as_of=self.now,
            limit=self.subject.BATCH_SIZE,
        )

    def test_should_reuse_the_same_incident_id_on_every_sweep(self) -> None:
        self.subject.execute()
        first_alert = self.repositories.events.add.call_args_list[-1].args[0]

        self.subject.execute()
        second_alert = self.repositories.events.add.call_args_list[-1].args[0]

        assert first_alert.payload.incident_id == second_alert.payload.incident_id

    def test_should_expire_audited_reconciliations_after_the_retention_window(
        self,
    ) -> None:
        self.subject.execute()

        self.repositories.external_effect_receipts.remove_reconciliations_before.assert_called_once_with(
            self.now - self.subject.RETENTION,
            limit=self.subject.BATCH_SIZE,
        )
