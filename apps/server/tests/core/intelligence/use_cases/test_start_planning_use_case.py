from typing import cast
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases.start_planning_use_case import (
    StartPlanningUseCase,
)
from shifu.shared.core.interfaces import IdentifierProvider


class TestStartPlanningUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories,
            instance=True,
        )
        self.planning_sessions_repository = self.repositories.planning_sessions
        self.events_repository = self.repositories.events
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.id_provider.generate.return_value = '01JPLANNING00000000000001'
        self.subject = StartPlanningUseCase(self.database, self.id_provider)

    def test_should_persist_exactly_one_planning_session_with_minted_id(self) -> None:
        result = self.subject.execute(
            '01JACCOUNT000000000000000001',
            'Quero aprender inglês em três meses',
        )

        self.database.transaction.assert_called_once_with()
        self.planning_sessions_repository.add.assert_called_once()
        persisted = cast(
            'PlanningSession',
            self.planning_sessions_repository.add.call_args.args[0],
        )
        assert persisted.id == '01JPLANNING00000000000001'
        assert persisted.account_id == '01JACCOUNT000000000000000001'
        assert persisted.initial_intent == 'Quero aprender inglês em três meses'
        assert result == persisted
        self.id_provider.generate.assert_called_once_with()

    def test_should_return_the_persisted_planning_session(self) -> None:
        result = self.subject.execute(
            '01JACCOUNT000000000000000002',
            'Quero me preparar para uma certificação',
        )

        assert isinstance(result, PlanningSession)
        assert result.id == '01JPLANNING00000000000001'
        assert result.account_id == '01JACCOUNT000000000000000002'
        assert result.initial_intent == 'Quero me preparar para uma certificação'

    def test_should_not_touch_the_events_repository(self) -> None:
        self.subject.execute(
            '01JACCOUNT000000000000000003',
            'Quero organizar meus estudos',
        )

        self.events_repository.add.assert_not_called()

    def test_should_propagate_repository_failure_without_returning_a_session(
        self,
    ) -> None:
        error = RuntimeError('database unavailable')
        self.planning_sessions_repository.add.side_effect = error

        with pytest.raises(RuntimeError, match='database unavailable'):
            self.subject.execute(
                '01JACCOUNT000000000000000004',
                'Quero aprender a tocar violão',
            )
