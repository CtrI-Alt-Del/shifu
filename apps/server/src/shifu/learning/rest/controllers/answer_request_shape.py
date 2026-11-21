"""Shared `AnswerRequest` shape validation for the preview and submit controllers.

Both controllers accept the same discriminated answer envelope (code files,
translation text, ordered steps, matched pairs, blanks or choices). Reject mixed shapes and
omits the fields its own `kind` requires.
"""

_FIELD_BY_KIND = {
    'ordering': 'ordered_step_keys',
    'fill_blanks': 'placements',
    'javascript_stdin': 'files',
    'react': 'files',
    'html_css_js': 'files',
    'react_fastify': 'files',
    'translation': 'text',
    'pair_matching': 'pairs',
}
_ERROR_BY_FIELD = {
    'ordered_step_keys': 'Ordering answers require ordered step keys only',
    'placements': 'Fill-blanks answers require placements only',
    'files': 'Code answers require files only',
    'text': 'Translation answers require text only',
    'pairs': 'Pair matching answers require pairs only',
    'selected_option_keys': 'Choice answers require selected option keys only',
}


def validate_answer_request_shape(
    kind: str | None,
    text: str | None,
    files: object | None,
    selected_option_keys: object | None,
    ordered_step_keys: object | None = None,
    placements: object | None = None,
    pairs: object | None = None,
) -> None:
    """Exactly the field owned by the answer kind must be present."""
    fields: dict[str, object | None] = {
        'selected_option_keys': selected_option_keys,
        'files': files,
        'text': text,
        'placements': placements,
        'pairs': pairs,
        'ordered_step_keys': ordered_step_keys,
    }
    required = _FIELD_BY_KIND.get(kind or '', 'selected_option_keys')
    value = fields[required]
    is_missing = (
        value is None
        or (required == 'text' and not str(value).strip())
        or (required == 'pairs' and not value)
    )
    has_other_field = any(
        other is not None for name, other in fields.items() if name != required
    )
    if is_missing or has_other_field:
        raise ValueError(_ERROR_BY_FIELD[required])
