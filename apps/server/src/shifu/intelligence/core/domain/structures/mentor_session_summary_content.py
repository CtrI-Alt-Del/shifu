from shifu.shared.core.domain.structures import structure


@structure
class MentorSessionSummaryContent:
    version: int
    text: str
    covered_message_count: int
    first_message_id: str
