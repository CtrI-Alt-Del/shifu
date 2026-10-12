from typing import Protocol
from shifu.shared.core.domain.structures import MentorContextSnapshot
from shifu.intelligence.core.domain.structures import MentorRouteResult


class MentorRouteProvider(Protocol):
    def route(
        self, content: str, context: MentorContextSnapshot
    ) -> MentorRouteResult: ...
