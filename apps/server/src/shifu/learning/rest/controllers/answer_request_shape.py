"""Shared `AnswerRequest` shape validation for the preview and submit controllers.

Both controllers accept the same discriminated answer envelope (code files,
translation text, ordered steps, or a choice selection) and must reject one that mixes or
omits the fields its own `kind` requires.
"""


def validate_answer_request_shape(
    kind: str | None,
    text: str | None,
    files: object | None,
    selected_option_keys: object | None,
    ordered_step_keys: object | None = None,
) -> None:
    if kind == 'ordering':
        if (
            ordered_step_keys is None
            or text is not None
            or files is not None
            or selected_option_keys is not None
        ):
            raise ValueError('Ordering answers require ordered step keys only')
        return
    if ordered_step_keys is not None:
        raise ValueError('Only ordering answers accept ordered step keys')
    if kind in {'javascript_stdin', 'react', 'html_css_js', 'react_fastify'}:
        if files is None or selected_option_keys is not None or text is not None:
            raise ValueError('Code answers require files only')
    elif kind == 'translation':
        if (
            text is None
            or not text.strip()
            or files is not None
            or selected_option_keys is not None
        ):
            raise ValueError('Translation answers require text only')
    elif selected_option_keys is None or files is not None or text is not None:
        raise ValueError('Choice answers require selected option keys only')
