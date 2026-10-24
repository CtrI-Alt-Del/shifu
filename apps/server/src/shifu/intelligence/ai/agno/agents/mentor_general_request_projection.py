"""Closed projection of a general (non-attachment) Mentor request.

The writer and the reviewer receive this projection instead of the whole request.
It keeps the conversation and the authorized state, and leaves out technical
identifiers, attachment file names and timestamps.
"""

from typing import Final

from shifu.intelligence.core.domain.structures import (
    MentorGenerationRequest,
    MentorResponseBlock,
)


MEMORY_LABEL: Final = 'declaração do aprendiz, não domínio comprovado'

# Account-wide lists stay out; only the facts of a resolved Objetivo travel.
_ACCOUNT_WIDE_FACTS: Final = frozenset(
    {'goals', 'completed_skills', 'progress_overview'}
)


def project_general_request(request: MentorGenerationRequest) -> dict[str, object]:
    context = request.context
    projection: dict[str, object] = {
        'requested_part': request.requested_part,
        'block_key': 'generated-0',
        'ordinal': len(request.approved_blocks),
        'history': [
            {'role': message.role.value, 'content': message.content}
            for message in request.history
        ],
        'context': {
            'diagnostic_in_progress': context.diagnostic_in_progress,
            'skill_completed': context.skill_completed,
            'unavailable_sources': list(context.unavailable_sources),
            'facts': [
                {'key': key, 'value': value}
                for key, value in context.facts
                if context.goal_id is not None and key not in _ACCOUNT_WIDE_FACTS
            ],
        },
        'approved_blocks': [
            {
                'block_key': block.block_key,
                'ordinal': block.ordinal,
                'content': block.content,
            }
            for block in request.approved_blocks
        ],
        'correction': request.correction,
    }
    if request.summary is not None:
        projection['summary'] = {
            'text': request.summary.text,
            'topics': list(request.summary.topics),
        }
    if request.memories:
        projection['memories'] = [
            {
                'category': memory.category.value,
                'content': memory.content,
                'label': MEMORY_LABEL,
            }
            for memory in request.memories
        ]
    return projection


def project_general_candidate(candidate: MentorResponseBlock) -> dict[str, object]:
    return {
        'block_key': candidate.block_key,
        'ordinal': candidate.ordinal,
        'content': candidate.content,
    }
