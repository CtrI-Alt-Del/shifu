"""Local Web Push service stub and VAPID test keys for push integration tests."""

import base64
import json
import os
import secrets
import time
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from typing import cast

import http_ece  # pyright: ignore[reportMissingTypeStubs]
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

_PUSH_ENVIRONMENT_NAMES = (
    'SHIFU_WEB_PUSH_VAPID_PRIVATE_KEY',
    'SHIFU_WEB_PUSH_VAPID_PUBLIC_KEY',
    'SHIFU_WEB_PUSH_SUBJECT',
    'SHIFU_WEB_PUSH_TIMEOUT_SECONDS',
)


def _urlsafe(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


@dataclass(frozen=True, slots=True)
class PushVapidKeys:
    """Server-side VAPID key pair generated once per test session."""

    private_key: str
    public_key: str
    subject: str


@dataclass(frozen=True, slots=True)
class PushBrowserKeys:
    """A browser subscription key pair able to decrypt what the server sends."""

    p256dh: str
    auth: str
    _private_key: ec.EllipticCurvePrivateKey
    _auth_bytes: bytes

    @classmethod
    def generate(cls) -> 'PushBrowserKeys':
        private_key = ec.generate_private_key(ec.SECP256R1())
        auth_bytes = secrets.token_bytes(16)
        public_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        return cls(
            p256dh=_urlsafe(public_bytes),
            auth=_urlsafe(auth_bytes),
            _private_key=private_key,
            _auth_bytes=auth_bytes,
        )

    def decrypt(self, body: bytes) -> dict[str, object]:
        plaintext = http_ece.decrypt(  # pyright: ignore[reportUnknownMemberType]
            body,
            private_key=self._private_key,
            auth_secret=self._auth_bytes,
            version='aes128gcm',
        )
        return cast('dict[str, object]', json.loads(plaintext))


@dataclass(frozen=True, slots=True)
class PushServiceRequest:
    """One request the stub received from the server's push provider."""

    name: str
    body: bytes
    content_encoding: str | None
    ttl: str | None
    has_vapid_authorization: bool
    received_at: float


class PushServiceStub:
    """A programmable Web Push service listening on a local plain-HTTP port.

    A redirect status answers with a `Location` pointing at the `REDIRECT_TARGET`
    endpoint, so a test can prove the server never follows it.
    """

    REDIRECT_STATUSES = frozenset({301, 302, 307, 308})
    REDIRECT_TARGET = 'redirect-target'

    def __init__(self) -> None:
        self._lock = Lock()
        self._programs: dict[str, list[int]] = {}
        self._requests: dict[str, list[PushServiceRequest]] = defaultdict(list)
        stub = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def do_POST(self) -> None:
                name = self.path.rsplit('/', 1)[-1]
                length = int(self.headers.get('content-length', '0'))
                body = self.rfile.read(length)
                authorization = self.headers.get('authorization', '')
                status = stub._record(
                    PushServiceRequest(
                        name=name,
                        body=body,
                        content_encoding=self.headers.get('content-encoding'),
                        ttl=self.headers.get('ttl'),
                        has_vapid_authorization=authorization.lower().startswith(
                            'vapid '
                        ),
                        received_at=time.time(),
                    )
                )
                payload = f'stub status {status}'.encode()
                self.send_response(status)
                if status in stub.REDIRECT_STATUSES:
                    self.send_header('location', stub.endpoint(stub.REDIRECT_TARGET))
                self.send_header('content-length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
        self._thread = Thread(
            target=self._server.serve_forever,
            name='shifu-push-service-stub',
            daemon=True,
        )

    @property
    def base_url(self) -> str:
        return f'http://127.0.0.1:{self._server.server_address[1]}'

    def endpoint(self, name: str) -> str:
        """Return the subscription endpoint whose responses `program` controls."""
        return f'{self.base_url}/push/{name}'

    def program(self, name: str, *statuses: int) -> None:
        """Answer the next requests for `name` with `statuses`; the last repeats."""
        with self._lock:
            self._programs[name] = list(statuses)

    def requests(self, name: str | None = None) -> list[PushServiceRequest]:
        with self._lock:
            if name is not None:
                return list(self._requests[name])
            return [
                request for received in self._requests.values() for request in received
            ]

    def wait_for_requests(
        self, name: str, count: int, *, timeout: float = 90.0
    ) -> list[PushServiceRequest]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            received = self.requests(name)
            if len(received) >= count:
                return received
            time.sleep(0.1)
        raise AssertionError(
            f'The push stub received {len(self.requests(name))} of {count} '
            f'expected request(s) for {name!r} before the timeout'
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def _record(self, request: PushServiceRequest) -> int:
        with self._lock:
            self._requests[request.name].append(request)
            program = self._programs.get(request.name)
            if not program:
                return 201
            if len(program) > 1:
                return program.pop(0)
            return program[0]


@pytest.fixture(scope='session')
def push_vapid_keys() -> PushVapidKeys:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_value = private_key.private_numbers().private_value
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    return PushVapidKeys(
        private_key=_urlsafe(private_value.to_bytes(32, 'big')),
        public_key=_urlsafe(public_bytes),
        subject='mailto:push-tests@shifu.local',
    )


@pytest.fixture(scope='session', autouse=True)
def _push_vapid_environment(push_vapid_keys: PushVapidKeys) -> Iterator[None]:
    """Give the application processes this suite starts a deterministic key pair."""

    previous = {name: os.environ.get(name) for name in _PUSH_ENVIRONMENT_NAMES}
    os.environ['SHIFU_WEB_PUSH_VAPID_PRIVATE_KEY'] = push_vapid_keys.private_key
    os.environ['SHIFU_WEB_PUSH_VAPID_PUBLIC_KEY'] = push_vapid_keys.public_key
    os.environ['SHIFU_WEB_PUSH_SUBJECT'] = push_vapid_keys.subject
    os.environ['SHIFU_WEB_PUSH_TIMEOUT_SECONDS'] = '5'
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.fixture
def push_service_stub() -> Iterator[PushServiceStub]:
    stub = PushServiceStub()
    stub.start()
    try:
        yield stub
    finally:
        stub.stop()
