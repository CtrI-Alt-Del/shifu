from typing import Protocol

from shifu.intelligence.core.domain.entities.planning_session import PlanningSession


class PlanningSessionsRepository(Protocol):
    def add(self, session: PlanningSession) -> None:
        """Store a new planning; raise a conflict when the id already exists."""
        ...

    def find_by_id(self, planning_id: str) -> PlanningSession | None: ...

    def update(self, session: PlanningSession) -> bool:
        """Compare-and-set on `session.version`; increment it when the write wins."""
        ...

    def remove(self, planning_id: str) -> bool: ...
