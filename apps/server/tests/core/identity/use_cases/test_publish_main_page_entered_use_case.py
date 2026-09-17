from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.identity.core.use_cases.publish_main_page_entered_use_case import (
    PublishMainPageEnteredUseCase,
)

if TYPE_CHECKING:
    from shifu.identity.core.domain.events import MainPageEnteredEvent


class TestPublishMainPageEnteredUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.identity_database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(
            IdentityDatabaseRepositories,
            instance=True,
        )
        self.events_repository = self.repositories.events
        self.identity_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.id_provider.generate.return_value = '01JEVENT000000000000000001'
        self.clock_provider.now.return_value = datetime(
            2026,
            1,
            3,
            12,
            30,
            tzinfo=UTC,
        )
        self.subject = PublishMainPageEnteredUseCase(
            self.identity_database,
            self.id_provider,
            self.clock_provider,
        )

    def test_should_add_canonical_event_inside_one_transaction(self) -> None:
        self.subject.execute('01JACCOUNT000000000000000001')

        self.identity_database.transaction.assert_called_once_with()
        self.events_repository.add.assert_called_once()
        event = cast(
            'MainPageEnteredEvent', self.events_repository.add.call_args.args[0]
        )
        assert event.name == 'app/main-page.entered'
        assert event.payload.event_id == '01JEVENT000000000000000001'
        assert event.payload.account_id == '01JACCOUNT000000000000000001'
        assert event.payload.occurred_at == '2026-01-03T12:30:00+00:00'
        self.id_provider.generate.assert_called_once_with()
        self.clock_provider.now.assert_called_once_with()

    def test_should_propagate_repository_failure(self) -> None:
        error = RuntimeError('database unavailable')
        self.events_repository.add.side_effect = error

        with pytest.raises(RuntimeError, match='database unavailable'):
            self.subject.execute('01JACCOUNT000000000000000001')
