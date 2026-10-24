from shifu.intelligence.core.domain.structures.mentor_response_block import (
    MentorResponseBlock,
)
from shifu.intelligence.core.domain.structures.mentor_intent_match import (
    MentorIntentMatch,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorRouteResult:
    intents: tuple[MentorIntentMatch, ...]
    local_blocks: tuple[MentorResponseBlock, ...]
    generation_requests: tuple[str, ...]
    clarification: str | None
    proposed_reference_ids: tuple[str, ...] = ()
    unanswered_requests: tuple[
        str, ...
    ] = ()  # generation requests without a curated FAQ answer
