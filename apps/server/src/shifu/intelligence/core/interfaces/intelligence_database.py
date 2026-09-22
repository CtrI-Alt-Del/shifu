from contextlib import AbstractContextManager
from typing import Protocol

from shifu.intelligence.core.interfaces.planning_sessions_repository import (
    PlanningSessionsRepository,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.interfaces import EventsRepository


@structure
class IntelligenceDatabaseRepositories:
    planning_sessions: PlanningSessionsRepository
    events: EventsRepository


class IntelligenceDatabase(Protocol):
    def transaction(
        self,
    ) -> AbstractContextManager[IntelligenceDatabaseRepositories]:
        """Open the sole transaction boundary for one Intelligence operation."""
        ...
