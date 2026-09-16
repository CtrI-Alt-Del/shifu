from typing import Protocol

from shifu.curriculum.core.domain.entities import Activity


class ActivitiesRepository(Protocol):
    def find_by_id(self, activity_id: str) -> Activity | None: ...

    def find_many_by_ids(self, activity_ids: tuple[str, ...]) -> list[Activity]: ...

    def find_many_by_competency_id(self, competency_id: str) -> list[Activity]: ...
