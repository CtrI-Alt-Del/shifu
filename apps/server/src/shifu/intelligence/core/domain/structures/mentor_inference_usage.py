from shifu.shared.core.domain.structures import structure


@structure
class MentorInferenceUsage:
    call_key: str
    profile: str
    used_tokens: int | None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
