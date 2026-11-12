from shifu.shared.core.domain.structures import structure


@structure
class AiTokenCount:
    input_tokens: int | None
    output_tokens: int | None
    used_tokens: int | None
