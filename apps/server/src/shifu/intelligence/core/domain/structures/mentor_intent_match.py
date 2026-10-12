from shifu.intelligence.core.domain.enums import MentorIntent
from shifu.shared.core.domain.structures import structure


@structure
class MentorIntentMatch:
    intent: MentorIntent
    similarity: float
