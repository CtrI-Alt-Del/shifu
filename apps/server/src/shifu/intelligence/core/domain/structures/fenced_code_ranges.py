import re

_FENCE_LINE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')


def fenced_code_ranges(content: str) -> tuple[tuple[int, int], ...]:
    """Code-point ranges of fenced code blocks (``` or ~~~; unclosed runs to the end)."""
    ranges: list[tuple[int, int]] = []
    opened_at: int | None = None
    marker = ''
    offset = 0
    for line in content.split('\n'):
        match = _FENCE_LINE.match(line.rstrip('\r'))
        if opened_at is None:
            if match and not (match.group(1)[0] == '`' and '`' in match.group(2)):
                opened_at, marker = offset, match.group(1)
        elif (
            match
            and match.group(1)[0] == marker[0]
            and len(match.group(1)) >= len(marker)
            and not match.group(2).strip()
        ):
            ranges.append((opened_at, offset + len(line)))
            opened_at = None
        offset += len(line) + 1
    if opened_at is not None:
        ranges.append((opened_at, len(content)))
    return tuple(ranges)
