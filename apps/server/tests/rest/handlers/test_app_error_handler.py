import asyncio
import json
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

if TYPE_CHECKING:
    from fastapi import Request

from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.intelligence.rest.mentor_attachment_error_handler import (
    MentorAttachmentErrorHandler,
)


def test_attachment_validation_uses_narrow_safe_422_mapping() -> None:
    response = asyncio.run(
        MentorAttachmentErrorHandler.handle_invalid_error(
            cast('Request', Mock()), MentorAttachmentInvalidError()
        )
    )

    assert response.status_code == 422
    body = cast('bytes', response.body)
    assert json.loads(body.decode()) == {
        'code': 'malformed_attachment',
        'message': 'O arquivo não é válido ou não é compatível.',
    }
