from typing import Protocol

from shifu.intelligence.core.domain.entities import MentorMessage
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryContext,
    MentorConversationSummaryDraft,
)


class MentorConversationSummarizerProvider(Protocol):
    def summarize(
        self,
        messages: tuple[MentorMessage, ...],
        previous: MentorConversationSummaryContext | None,
    ) -> MentorConversationSummaryDraft: ...
