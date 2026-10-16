import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_MAX_MULTIPART_BYTES = 2_064_000
_UPLOAD_PATH_PREFIX = '/intelligence/mentor-attachment-batches/'
_UPLOAD_PATH_SUFFIX = '/attachments'


class MentorAttachmentBodyLimitMiddleware:
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
                await self._respond(
                    send,
                    400,
                    'malformed_attachment',
                    'Não foi possível ler este arquivo.',
                )
                return
            if length < 0:
                await self._respond(
                    send,
                    400,
                    'malformed_attachment',
                    'Não foi possível ler este arquivo.',
                )
                return
            if length > self._max_bytes:
                await self._respond(
                    send,
                    413,
                    'attachment_too_large',
                    'O arquivo excede o limite de 2 MB.',
                )
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
                await self._respond(
                    send,
                    413,
                    'attachment_too_large',
                    'O arquivo excede o limite de 2 MB.',
                )
                return None
            buffered.append(message)
            if not message.get('more_body', False):
                break
        return buffered

    @staticmethod
    def _is_upload(scope: Scope) -> bool:
        if scope.get('type') != 'http' or scope.get('method') != 'POST':
            return False
        path = str(scope.get('path', ''))
        return path.startswith(_UPLOAD_PATH_PREFIX) and path.endswith(
            _UPLOAD_PATH_SUFFIX
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
                    (b'cache-control', b'no-store'),
                ],
            }
        )
        await send({'type': 'http.response.body', 'body': body})
