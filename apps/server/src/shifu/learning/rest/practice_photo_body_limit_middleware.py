import json
import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_MAX_PHOTO_BYTES = 10 * 1024 * 1024
_MAX_MULTIPART_BYTES = _MAX_PHOTO_BYTES + 64_000
_UPLOAD_PATH = re.compile(
    r'^/learning/goals/[^/]+/skills/[^/]+/competencies/[^/]+'
    r'/activities/[^/]+/practice-draft/photos/[^/]+$'
)


class PracticePhotoBodyLimitMiddleware:
    """Bound the multipart body of the practice photo PUT before it is parsed."""

    def __init__(self, app: ASGIApp, max_bytes: int = _MAX_MULTIPART_BYTES) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._is_upload(scope):
            await self._app(scope, receive, send)
            return

        headers = dict(scope.get('headers', []))
        raw_length = headers.get(b'content-length')
        if raw_length is not None:
            try:
                length = int(raw_length)
            except ValueError:
                await self._respond_malformed(send)
                return

            if length < 0:
                await self._respond_malformed(send)
                return

            if length > self._max_bytes:
                await self._respond_too_large(send)
                return

        buffered = await self._buffer_request(receive, send)
        if buffered is None:
            return

        async def replay_receive() -> Message:
            if buffered:
                return buffered.pop(0)

            return await receive()

        await self._app(scope, replay_receive, send)

    async def _buffer_request(
        self, receive: Receive, send: Send
    ) -> list[Message] | None:
        buffered: list[Message] = []
        consumed = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return None

            if message['type'] != 'http.request':
                continue

            consumed += len(message.get('body', b''))
            if consumed > self._max_bytes:
                await self._respond_too_large(send)
                return None

            buffered.append(message)
            if not message.get('more_body', False):
                break

        return buffered

    @staticmethod
    def _is_upload(scope: Scope) -> bool:
        if scope.get('type') != 'http' or scope.get('method') != 'PUT':
            return False

        return _UPLOAD_PATH.fullmatch(str(scope.get('path', ''))) is not None

    @staticmethod
    async def _respond_malformed(send: Send) -> None:
        await PracticePhotoBodyLimitMiddleware._respond(
            send, 400, 'malformed_photo', 'Não foi possível ler esta foto.'
        )

    @staticmethod
    async def _respond_too_large(send: Send) -> None:
        await PracticePhotoBodyLimitMiddleware._respond(
            send, 413, 'photo_too_large', 'A foto excede o limite de 10 MB.'
        )

    @staticmethod
    async def _respond(send: Send, status_code: int, code: str, message: str) -> None:
        body = json.dumps({'code': code, 'message': message}).encode('utf-8')
        await send(
            {
                'type': 'http.response.start',
                'status': status_code,
                'headers': [
                    (b'content-type', b'application/json'),
                    (b'content-length', str(len(body)).encode('ascii')),
                    (b'cache-control', b'private, no-store'),
                ],
            }
        )
        await send({'type': 'http.response.body', 'body': body})
