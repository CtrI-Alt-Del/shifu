from typing import Protocol

from shifu.intelligence.core.domain.entities import PlanningSession


class PlanningSessionsRepository(Protocol):
    def add(self, planning_session: PlanningSession) -> None: ...

    def find_by_id(self, planning_session_id: str) -> PlanningSession | None: ...

    def remove_all(self) -> None: ...
