from shifu.shared.core.domain.structures import structure


@structure
class MentorMessageAiCharge:
    """Units charged for the response behind one Mentor message, with its month limit."""

    message_id: str
    attempt_id: str
    charged_units: int
    limit_units: int

    def __post_init__(self) -> None:
        if (
            not self.message_id
            or not self.attempt_id
            or self.charged_units < 0
            or self.limit_units <= 0
        ):
            raise ValueError('Invalid Mentor message AI charge')
