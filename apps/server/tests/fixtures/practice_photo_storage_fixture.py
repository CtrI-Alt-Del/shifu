"""Private practice photo storage doubles and image builders for Learning tests."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from typing import cast

from PIL import Image

from shifu.shared.core.domain.errors import ServiceUnavailableError

_S3_PATH = re.compile(r'^/(?P<bucket>[^/]+)/(?P<key>.+)$')
_FORMATS = {
    'image/jpeg': ('JPEG', '.jpg'),
    'image/png': ('PNG', '.png'),
    'image/webp': ('WEBP', '.webp'),
}


class PracticePhotoImages:
    """Build small valid images in the three accepted formats."""

    @staticmethod
    def build(media_type: str = 'image/jpeg', size: tuple[int, int] = (8, 8)) -> bytes:
        image_format, _ = _FORMATS[media_type]
        buffer = io.BytesIO()
        Image.new('RGB', size, (200, 120, 40)).save(buffer, format=image_format)
        return buffer.getvalue()

    @staticmethod
    def extension(media_type: str) -> str:
        return _FORMATS[media_type][1]

    @staticmethod
    def file(
        media_type: str = 'image/jpeg', name: str = 'prato'
    ) -> tuple[str, bytes, str]:
        extension = PracticePhotoImages.extension(media_type)
        return (
            f'{name}{extension}',
            PracticePhotoImages.build(media_type),
            media_type,
        )


@dataclass
class PracticePhotoStorageStub:
    """In-memory FileStorageProvider with switchable failures."""

    objects: dict[str, bytes] = field(default_factory=dict[str, bytes])
    fail_put: bool = False
    fail_remove: bool = False
    removed_keys: list[str] = field(default_factory=list[str])

    def put(self, object_key: str, content: bytes, media_type: str) -> None:
        if self.fail_put:
            raise ServiceUnavailableError
        self.objects[object_key] = content

    def read(self, object_key: str) -> bytes:
        if object_key not in self.objects:
            raise ServiceUnavailableError
        return self.objects[object_key]

    def remove(self, object_key: str) -> None:
        if self.fail_remove:
            raise ServiceUnavailableError
        self.objects.pop(object_key, None)
        self.removed_keys.append(object_key)


class _S3Handler(BaseHTTPRequestHandler):
    @property
    def stub(self) -> PracticePhotoS3Stub:
        return cast('_S3Server', self.server).stub

    def _key(self) -> str | None:
        match = _S3_PATH.match(self.path.split('?', maxsplit=1)[0])
        if match is None or match.group('bucket') != self.stub.bucket:
            return None
        return match.group('key')

    def _reply(self, status: int, body: bytes = b'') -> None:
        self.send_response(status)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self) -> None:
        key = self._key()
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        if key is None:
            self._reply(404)
            return
        self.stub.put(key, body)
        self._reply(200)

    def do_GET(self) -> None:
        key = self._key()
        body = self.stub.get(key) if key is not None else None
        if body is None:
            self._reply(404)
            return
        self._reply(200, body)

    def do_DELETE(self) -> None:
        key = self._key()
        if key is not None:
            self.stub.discard(key)
        self._reply(204)

    def log_message(self, format: str, *args: object) -> None:
        return


class _S3Server(ThreadingHTTPServer):
    def __init__(self, stub: PracticePhotoS3Stub) -> None:
        super().__init__(('0.0.0.0', 0), _S3Handler)  # noqa: S104 - the app process must reach it
        self.stub = stub


class PracticePhotoS3Stub:
    """Tiny path-style S3 server that lets a real process use boto3 against memory."""

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        self._objects: dict[str, bytes] = {}
        self._lock = Lock()
        self._server = _S3Server(self)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def put(self, key: str, content: bytes) -> None:
        with self._lock:
            self._objects[key] = content

    def get(self, key: str) -> bytes | None:
        with self._lock:
            return self._objects.get(key)

    def discard(self, key: str) -> None:
        with self._lock:
            self._objects.pop(key, None)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._objects
