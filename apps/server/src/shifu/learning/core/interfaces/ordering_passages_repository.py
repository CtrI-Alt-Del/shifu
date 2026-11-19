from typing import Protocol

from shifu.learning.core.domain.entities import OrderingPassage


class OrderingPassagesRepository(Protocol):
    def find_active(
        self, skill_experience_id: str, activity_id: str
    ) -> OrderingPassage | None: ...

    def find_by_key(
        self,
        skill_experience_id: str,
        activity_id: str,
        passage_key: str,
    ) -> OrderingPassage | None: ...

    def add(self, passage: OrderingPassage) -> None: ...

    def update(self, passage: OrderingPassage) -> None: ...
