from typing import Protocol

from shifu.shared.core.domain.structures import MentorGoalDestinations


class MentorGoalDestinationsProvider(Protocol):
    def read(self, account_id: str, skill_id: str) -> MentorGoalDestinations: ...
