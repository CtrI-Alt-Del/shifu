from typing import Literal
from urllib.parse import unquote, urlsplit

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumReactFastifyHttpExampleSnapshot:
    key: str
    title: str
    method: Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
    path: str
    body: str | None = None

    def __post_init__(self) -> None:
        for value in (self.key, self.title):
            NonEmptyText.create(value, error_type=ValidationError)
        decoded = unquote(self.path)
        parsed = urlsplit(decoded)
        if (
            self.method
            not in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}
            or not (decoded == '/api' or decoded.startswith('/api/'))
            or parsed.scheme
            or parsed.netloc
            or parsed.fragment
            or '\\' in decoded
            or any(ord(char) < 32 or ord(char) == 127 for char in decoded)
            or any(part in {'.', '..'} for part in parsed.path.split('/'))
            or '%' in decoded
            or (self.method in {'GET', 'HEAD'} and self.body is not None)
            or (self.body is not None and len(self.body.encode('utf-8')) > 65536)
        ):
            raise ValidationError
