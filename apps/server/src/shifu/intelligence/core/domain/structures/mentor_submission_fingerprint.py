import hashlib
import json
from dataclasses import asdict

from shifu.intelligence.core.domain.structures.mentor_context_hint import (
    MentorContextHint,
)


def mentor_submission_fingerprint(content: str, hint: MentorContextHint | None) -> str:
    canonical_hint = asdict(hint) if hint is not None else None
    if canonical_hint is not None and not any(canonical_hint.values()):
        canonical_hint = None
    payload = json.dumps(
        {'version': 1, 'content': content, 'hint': canonical_hint},
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def mentor_submission_fingerprint_v2(
    content: str,
    hint: MentorContextHint | None,
    attachments: tuple[tuple[str, str], ...],
) -> str:
    canonical_hint = asdict(hint) if hint is not None else None
    if canonical_hint is not None and not any(canonical_hint.values()):
        canonical_hint = None
    payload = json.dumps(
        {
            'version': 2,
            'content': content,
            'hint': canonical_hint,
            'attachments': [
                {'attachment_id': attachment_id, 'checksum': checksum}
                for attachment_id, checksum in attachments
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    )
    return hashlib.sha256(payload.encode()).hexdigest()
