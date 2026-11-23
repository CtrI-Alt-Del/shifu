from shifu.intelligence.core.domain.structures.mentor_message_ai_usage import (
    MentorMessageAiUsage,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorSessionAiUsage:
    items: tuple[MentorMessageAiUsage, ...]
