from datetime import UTC, datetime
from unittest.mock import create_autospec
from uuid import uuid4

import pytest

from shifu.identity.core.domain.errors import ExternalEffectReceiptReconciliationError
from shifu.identity.core.domain.structures import AccountExternalEffectReceiptAdmission
from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases import (
    ListUnresolvedAccountExternalEffectReceiptsUseCase,
)


class TestListUnresolvedAccountExternalEffectReceiptsUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.receipts = (
            AccountExternalEffectReceiptAdmission(
                account_id='01SHF000000000000000000001',
                effect_id=uuid4(),
                operation='communication.email.send',
                admitted_at=datetime(2026, 11, 21, tzinfo=UTC),
                state='unknown',
                is_new=False,
            ),
        )
        self.repositories.external_effect_receipts.list_unresolved.return_value = (
            self.receipts
        )
        self.subject = ListUnresolvedAccountExternalEffectReceiptsUseCase(self.database)

    def test_should_list_unresolved_receipts_with_a_bounded_limit(self) -> None:
        assert self.subject.execute(25) == self.receipts

        self.repositories.external_effect_receipts.list_unresolved.assert_called_once_with(
            25
        )

    @pytest.mark.parametrize('limit', [0, -1, 1001])
    def test_should_reject_out_of_range_limits(self, limit: int) -> None:
        with pytest.raises(ExternalEffectReceiptReconciliationError):
            self.subject.execute(limit)

        self.repositories.external_effect_receipts.list_unresolved.assert_not_called()
