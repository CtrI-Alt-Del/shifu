from typing import Protocol

from shifu.shared.core.domain.structures import MentorContextSnapshot


class MentorContextProvider(Protocol):
    def read(
        self,
        account_id: str,
        reference_ids: tuple[str, ...],
        *,
        goal_id: str | None = None,
        skill_id: str | None = None,
        competency_id: str | None = None,
        material_id: str | None = None,
        activity_id: str | None = None,
    ) -> MentorContextSnapshot: ...
