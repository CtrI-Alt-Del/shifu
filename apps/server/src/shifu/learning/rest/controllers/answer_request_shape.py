"""Shared `AnswerRequest` shape validation for the preview and submit controllers.

Both controllers accept the same discriminated answer envelope (code files,
translation text, matched pairs, or a choice selection) and must reject one that mixes or
omits the fields its own `kind` requires.
"""


def validate_answer_request_shape(
    kind: str | None,
    text: str | None,
    files: object | None,
    selected_option_keys: object | None,
    pairs: object | None = None,
) -> None:
    if kind in {'javascript_stdin', 'react', 'html_css_js', 'react_fastify'}:
        if (
            files is None
            or selected_option_keys is not None
            or text is not None
            or pairs is not None
        ):
            raise ValueError('Code answers require files only')
    elif kind == 'translation':
        if (
            text is None
            or not text.strip()
            or files is not None
            or selected_option_keys is not None
            or pairs is not None
        ):
            raise ValueError('Translation answers require text only')
    elif kind == 'pair_matching':
        if (
            not pairs
            or files is not None
            or selected_option_keys is not None
            or text is not None
        ):
            raise ValueError('Pair matching answers require pairs only')
    elif (
        selected_option_keys is None
        or files is not None
        or text is not None
        or pairs is not None
    ):
        raise ValueError('Choice answers require selected option keys only')
