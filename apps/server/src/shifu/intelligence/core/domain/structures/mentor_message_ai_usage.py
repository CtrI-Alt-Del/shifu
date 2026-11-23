from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class MentorMessageAiUsage:
    """Share of the monthly AI quota that the response behind one message spent."""

    message_id: str
    attempt_id: str
    percentage: Decimal
