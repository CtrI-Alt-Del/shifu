from shifu.intelligence.core.domain.structures import MentorMessageAiCharge


class MentorMessageAiChargeMapper:
    @staticmethod
    def to_structure(
        message_id: str, attempt_id: str, charged_units: int, limit_units: int
    ) -> MentorMessageAiCharge:
        return MentorMessageAiCharge(
            message_id=message_id,
            attempt_id=attempt_id,
            charged_units=charged_units,
            limit_units=limit_units,
        )
