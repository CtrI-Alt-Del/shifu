import asyncio
from collections.abc import Iterator
from typing import cast

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from shifu.app import ActivityPayloadLimitMiddleware


class TestActivityPayloadLimitMiddleware:
    def test_should_pass_through_requests_outside_the_limited_route(self) -> None:
        async def assert_passes_through(scope: Scope) -> None:
            observed: list[Message] = []
            calls = 0

            async def app(
                _scope: Scope,
                receive: Receive,
                _send: Send,
            ) -> None:
                nonlocal calls
                calls += 1
                observed.append(await receive())

            async def receive() -> Message:
                return {'type': 'http.request', 'body': b'body'}

            async def send(_message: Message) -> None:
                return None

            middleware = ActivityPayloadLimitMiddleware(app, max_body_bytes=1)
            await middleware(scope, receive, send)

            assert calls == 1
            assert observed == [{'type': 'http.request', 'body': b'body'}]

        for scope in (
            {'type': 'websocket', 'path': '/learning/activities/activity-1'},
            {'type': 'http', 'method': 'GET', 'path': '/learning/activities/a'},
            {'type': 'http', 'method': 'POST', 'path': '/other/activities/a'},
            {'type': 'http', 'method': 'POST', 'path': '/learning/goals/goal-1'},
        ):
            asyncio.run(assert_passes_through(cast('Scope', scope)))

    def test_should_ignore_non_request_messages_and_replay_buffered_chunks(
        self,
    ) -> None:
        scope = cast(
            'Scope',
            {
                'type': 'http',
                'method': 'POST',
                'path': '/learning/goals/goal-1/activities/activity-1/attempts',
            },
        )
        incoming = iter(
            [
                {'type': 'lifespan.startup'},
                {'type': 'http.request', 'body': b'12', 'more_body': True},
                {'type': 'http.request', 'body': b'34', 'more_body': False},
                {'type': 'http.disconnect'},
            ]
        )
        observed: list[Message] = []

        async def receive() -> Message:
            return next(incoming)

        async def send(_message: Message) -> None:
            return None

        async def app(
            _scope: Scope,
            replay_receive: Receive,
            _send: Send,
        ) -> None:
            for _ in range(3):
                observed.append(await replay_receive())

        middleware = ActivityPayloadLimitMiddleware(app, 4)
        asyncio.run(middleware(scope, receive, send))

        assert observed == [
            {'type': 'http.request', 'body': b'12', 'more_body': True},
            {'type': 'http.request', 'body': b'34', 'more_body': False},
            {'type': 'http.disconnect'},
        ]

    def test_should_stop_when_the_client_disconnects_while_buffering(self) -> None:
        scope = cast(
            'Scope',
            {
                'type': 'http',
                'method': 'POST',
                'path': '/learning/goals/goal-1/activities/activity-1/attempts',
            },
        )
        called = False
        sent: list[Message] = []

        async def receive() -> Message:
            return {'type': 'http.disconnect'}

        async def send(message: Message) -> None:
            sent.append(message)

        async def app(_scope: Scope, _receive: Receive, _send: Send) -> None:
            nonlocal called
            called = True

        middleware = ActivityPayloadLimitMiddleware(app, 4)
        asyncio.run(middleware(scope, receive, send))

        assert not called
        assert sent == []

    def test_should_buffer_and_replay_a_body_under_the_limit(self) -> None:
        app = self._application(max_body_bytes=4)

        with TestClient(app) as client:
            response = client.post(
                '/learning/goals/goal-1/activities/activity-1/attempts',
                content=b'1234',
            )

        assert response.status_code == 200
        assert response.json() == {'body_bytes': 4}

    def test_should_reject_a_chunked_body_that_exceeds_the_limit(self) -> None:
        app = self._application(max_body_bytes=3)

        def body_chunks() -> Iterator[bytes]:
            yield b'12'
            yield b'34'

        with TestClient(app) as client:
            response = client.post(
                '/learning/goals/goal-1/activities/activity-1/attempts',
                content=body_chunks(),
            )

        assert response.status_code == 413
        assert response.json() == {
            'detail': 'A resposta enviada excede o limite permitido.'
        }

    @staticmethod
    def _application(max_body_bytes: int) -> FastAPI:
        app = FastAPI()
        app.add_middleware(
            ActivityPayloadLimitMiddleware,
            max_body_bytes=max_body_bytes,
        )

        @app.post('/learning/goals/{goal_id}/activities/{activity_id}/attempts')
        async def submit(request: Request) -> dict[str, int]:
            return {'body_bytes': len(await request.body())}

        return app
