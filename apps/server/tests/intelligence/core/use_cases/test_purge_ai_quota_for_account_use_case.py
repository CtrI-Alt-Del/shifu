from unittest.mock import Mock, call, create_autospec

import pytest

from shifu.intelligence.core.interfaces import (
    AiQuotaChargesRepository,
    AiQuotaMonthsRepository,
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import PurgeAiQuotaForAccountUseCase


class TestPurgeAiQuotaForAccountUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.months = create_autospec(AiQuotaMonthsRepository, instance=True)
        self.charges = create_autospec(AiQuotaChargesRepository, instance=True)
        self.repositories.ai_quota_months = self.months
        self.repositories.ai_quota_charges = self.charges
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = PurgeAiQuotaForAccountUseCase(self.database)

    def test_should_lock_the_months_before_removing_charges_then_months(self) -> None:
        self.charges.remove_by_account_id.return_value = 2
        self.months.remove_by_account_id.return_value = 3
        effects = Mock()
        effects.attach_mock(self.months.lock_by_account_id, 'lock')
        effects.attach_mock(self.charges.remove_by_account_id, 'charges')
        effects.attach_mock(self.months.remove_by_account_id, 'months')

        assert self.subject.execute('account') == 5

        assert effects.mock_calls == [
            call.lock('account'),
            call.charges('account'),
            call.months('account'),
        ]
        self.database.transaction.assert_called_once()

    def test_should_return_zero_on_repeated_delivery(self) -> None:
        self.charges.remove_by_account_id.side_effect = [1, 0]
        self.months.remove_by_account_id.side_effect = [1, 0]

        assert self.subject.execute('account') == 2
        assert self.subject.execute('account') == 0

    def test_should_only_touch_the_given_account(self) -> None:
        self.subject.execute('account')

        self.months.lock_by_account_id.assert_called_once_with('account')
        self.charges.remove_by_account_id.assert_called_once_with('account')
        self.months.remove_by_account_id.assert_called_once_with('account')
        self.months.ensure_and_lock.assert_not_called()
