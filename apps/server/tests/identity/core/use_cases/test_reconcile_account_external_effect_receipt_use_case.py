from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import create_autospec
from uuid import uuid4

import pytest

from shifu.identity.core.domain.errors import ExternalEffectReceiptReconciliationError
from shifu.identity.core.domain.structures import (
    AccountExternalEffectReceiptReconciliation,
)
from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.providers.account_activity.sqlalchemy_account_activity_provider import (
    SqlalchemyAccountActivityProvider,
)
from shifu.identity.core.use_cases import ReconcileAccountExternalEffectReceiptUseCase
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.interfaces import ClockProvider

if TYPE_CHECKING:
    from tests.fixtures.postgres_fixture import PostgresDatabase


class TestReconcileAccountExternalEffectReceiptUseCase:
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
        self.reconciliation = AccountExternalEffectReceiptReconciliation(
            account_id='01SHF000000000000000000001',
            effect_id=uuid4(),
            operation='learning.code-rubric.assess',
            resolution='applied',
            operator_id='ops-identity-1',
            evidence_reference='INC-2048',
            evidence_sha256='a' * 64,
            confirm_no_live_operation=True,
        )
        self.repositories.external_effect_receipts.reconcile.return_value = True
        self.subject = ReconcileAccountExternalEffectReceiptUseCase(
            self.database, self.clock
        )

    def test_should_record_verified_applied_effect_and_settle_its_receipt(self) -> None:
        self.subject.execute(self.reconciliation)

        self.repositories.external_effect_receipts.reconcile.assert_called_once_with(
            self.reconciliation,
            reconciled_at=self.now,
            stale_before=self.now - timedelta(minutes=30),
        )

    def test_should_reject_evidence_without_recording_a_resolution(self) -> None:
        invalid = AccountExternalEffectReceiptReconciliation(
            account_id=self.reconciliation.account_id,
            effect_id=self.reconciliation.effect_id,
            operation=self.reconciliation.operation,
            resolution='applied',
            operator_id='ops-identity-1',
            evidence_reference='INC-2048',
            evidence_sha256='not-a-digest',
            confirm_no_live_operation=True,
        )

        with pytest.raises(ExternalEffectReceiptReconciliationError):
            self.subject.execute(invalid)

        self.repositories.external_effect_receipts.reconcile.assert_not_called()

    def test_should_reject_reconciliation_without_confirmation_of_remote_quiescence(
        self,
    ) -> None:
        unconfirmed = AccountExternalEffectReceiptReconciliation(
            account_id=self.reconciliation.account_id,
            effect_id=self.reconciliation.effect_id,
            operation=self.reconciliation.operation,
            resolution='applied',
            operator_id='ops-identity-1',
            evidence_reference='INC-2048',
            evidence_sha256='a' * 64,
            confirm_no_live_operation=False,
        )

        with pytest.raises(ExternalEffectReceiptReconciliationError):
            self.subject.execute(unconfirmed)

        self.repositories.external_effect_receipts.reconcile.assert_not_called()

    def test_should_reject_a_receipt_that_changed_or_is_still_live(self) -> None:
        self.repositories.external_effect_receipts.reconcile.return_value = False

        with pytest.raises(ExternalEffectReceiptReconciliationError):
            self.subject.execute(self.reconciliation)

        self.repositories.external_effect_receipts.reconcile.assert_called_once()


class TestReconcileAccountExternalEffectReceiptPostgres:
    def test_unknown_receipt_must_be_stale_before_it_can_be_reconciled(
        self, postgres_database: PostgresDatabase
    ) -> None:
        database = SqlalchemyIdentityDatabase(postgres_database.engine)
        account = AccountFaker.fake()
        with database.transaction() as repositories:
            repositories.accounts.add(account)

        account_activity = SqlalchemyAccountActivityProvider(
            database, postgres_database.engine
        )
        effect_id = uuid4()
        operation = 'learning.code-rubric.assess'
        with (
            pytest.raises(RuntimeError, match='remote operation timed out'),
            account_activity.external_effect(account.id, effect_id, operation),
        ):
            raise RuntimeError('remote operation timed out')

        reconciliation = AccountExternalEffectReceiptReconciliation(
            account_id=account.id,
            effect_id=effect_id,
            operation=operation,
            resolution='not_applied',
            operator_id='ops-identity-1',
            evidence_reference='INC-2048',
            evidence_sha256='a' * 64,
            confirm_no_live_operation=True,
        )
        clock = create_autospec(ClockProvider, instance=True)
        current_time = datetime.now(UTC)
        clock.now.return_value = current_time
        subject = ReconcileAccountExternalEffectReceiptUseCase(database, clock)

        with pytest.raises(ExternalEffectReceiptReconciliationError):
            subject.execute(reconciliation)

        clock.now.return_value = current_time + timedelta(minutes=31)
        subject.execute(reconciliation)

        with database.transaction() as repositories:
            assert (
                repositories.external_effect_receipts.has_unresolved_for_account_id(
                    account.id
                )
                is False
            )
