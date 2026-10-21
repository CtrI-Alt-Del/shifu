import base64
import binascii
import json
from datetime import datetime
from typing import cast


class MentorCursor:
    @staticmethod
    def encode(payload: dict[str, str | None]) -> str:
        serialized = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()
        return base64.urlsafe_b64encode(serialized).decode().rstrip('=')

    @staticmethod
    def decode(cursor: str) -> dict[str, object]:
        if not cursor or len(cursor) > 2048:
            raise ValueError('Invalid cursor')
        try:
            raw = base64.urlsafe_b64decode(cursor + '=' * (-len(cursor) % 4))
            payload: object = json.loads(raw)
        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            binascii.Error,
        ) as error:
            raise ValueError('Invalid cursor') from error
        if not isinstance(payload, dict):
            raise TypeError('Invalid cursor')
        return cast('dict[str, object]', payload)

    @staticmethod
    def timestamp(value: object) -> datetime:
        if not isinstance(value, str):
            raise TypeError('Invalid cursor')
        try:
            return datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError('Invalid cursor') from error
