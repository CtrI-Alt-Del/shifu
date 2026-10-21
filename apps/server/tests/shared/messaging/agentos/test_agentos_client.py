import asyncio
import json
from urllib.parse import parse_qs

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from shifu.shared.messaging.agentos.agentos_client import (
    AgentOSClient,
    AgentOSClientError,
    PrivateAgentOSApp,
)

_SERVICE_TOKEN = 'test-private-service-token'


class TestAgentOSClient:
    def test_async_submission_uses_filtered_internal_route_and_safe_envelope(
        self,
    ) -> None:
        observed: list[tuple[str, dict[str, str], dict[str, str]]] = []

        async def exercise() -> dict[str, object]:
            async def submit(request: Request) -> JSONResponse:
                body = parse_qs((await request.body()).decode())
                fields = json.loads(body['message'][0])
                observed.append(
                    (
                        request.url.path,
                        fields,
                        {
                            name: value
                            for name, value in request.headers.items()
                            if name in {'x-shifu-agentos-token', 'authorization'}
                        },
                    )
                )
                return JSONResponse(
                    {'run_id': 'run-1', 'status': 'PENDING'}, status_code=202
                )

            app = Starlette(
                routes=[
                    Route('/workflows/mentor-workflow/runs', submit, methods=['POST'])
                ]
            )
            client = AgentOSClient(
                app,
                service_token=_SERVICE_TOKEN,
                workflow_ids=frozenset({'mentor-workflow'}),
            )
            await client.start()
            try:
                return await client.submit_workflow_async(
                    workflow_id='mentor-workflow',
                    fields={
                        'attachment_id': 'attachment-1',
                        'generation': '2',
                        'kind': 'learning',
                    },
                    background=True,
                    session_id='event-1',
                )
            finally:
                await client.close()

        receipt = asyncio.run(exercise())

        assert receipt == {'run_id': 'run-1', 'status': 'PENDING'}
        assert observed == [
            (
                '/workflows/mentor-workflow/runs',
                {
                    'attachment_id': 'attachment-1',
                    'generation': '2',
                    'kind': 'learning',
                },
                {},
            )
        ]

    def test_submission_rejects_unknown_workflows_and_private_envelope_fields(
        self,
    ) -> None:
        async def exercise() -> None:
            app = Starlette()
            client = AgentOSClient(
                app,
                service_token=_SERVICE_TOKEN,
                workflow_ids=frozenset({'mentor-workflow'}),
            )
            await client.start()
            await client.start()
            try:
                with pytest.raises(AgentOSClientError, match='not registered'):
                    await client.submit_workflow_async(
                        workflow_id='unregistered',
                        fields={'event_id': 'event-1'},
                        background=True,
                        session_id='event-1',
                    )
                with pytest.raises(AgentOSClientError, match='envelope is invalid'):
                    await client.submit_workflow_async(
                        workflow_id='mentor-workflow',
                        fields={'prompt': 'private attachment content'},
                        background=True,
                        session_id='event-1',
                    )
                with pytest.raises(AgentOSClientError, match='envelope is invalid'):
                    await client.submit_workflow_async(
                        workflow_id='mentor-workflow',
                        fields={'kind': 'administrator'},
                        background=True,
                        session_id='event-1',
                    )
            finally:
                await client.close()

        asyncio.run(exercise())

    def test_background_submission_requires_durable_admission(self) -> None:
        async def exercise() -> None:
            async def reject_admission(_request: Request) -> JSONResponse:
                return JSONResponse({'run_id': 'run-1', 'status': 'RUNNING'})

            app = Starlette(
                routes=[
                    Route(
                        '/workflows/mentor-workflow/runs',
                        reject_admission,
                        methods=['POST'],
                    )
                ]
            )
            client = AgentOSClient(
                app,
                service_token=_SERVICE_TOKEN,
                workflow_ids=frozenset({'mentor-workflow'}),
            )
            await client.start()
            try:
                with pytest.raises(AgentOSClientError, match='durably admit'):
                    await client.submit_workflow_async(
                        workflow_id='mentor-workflow',
                        fields={'event_id': 'event-1'},
                        background=True,
                        session_id='event-1',
                    )
            finally:
                await client.close()

        asyncio.run(exercise())

    def test_async_submission_requires_a_started_client(self) -> None:
        client = AgentOSClient(
            Starlette(),
            service_token=_SERVICE_TOKEN,
            workflow_ids=frozenset({'mentor-workflow'}),
        )

        async def exercise() -> None:
            with pytest.raises(AgentOSClientError, match='not available'):
                await client.submit_workflow_async(
                    workflow_id='mentor-workflow',
                    fields={'event_id': 'event-1'},
                    background=True,
                    session_id='event-1',
                )

        asyncio.run(exercise())

    def test_submission_hides_transport_and_response_errors(self) -> None:
        async def exercise() -> None:
            async def unavailable(_request: Request) -> JSONResponse:
                return JSONResponse(
                    {'detail': 'sensitive transport response'}, status_code=500
                )

            async def invalid_receipt(_request: Request) -> JSONResponse:
                return JSONResponse(['not', 'an', 'object'], status_code=200)

            async def transport_failure(_request: Request) -> JSONResponse:
                raise RuntimeError('private transport detail')

            for endpoint, expected_error in (
                (unavailable, 'request failed'),
                (invalid_receipt, 'invalid response'),
                (transport_failure, 'request failed'),
            ):
                app = Starlette(
                    routes=[Route('/workflows/title/runs', endpoint, methods=['POST'])]
                )
                client = AgentOSClient(
                    app,
                    service_token=_SERVICE_TOKEN,
                    workflow_ids=frozenset({'title'}),
                )
                await client.start()
                try:
                    with pytest.raises(AgentOSClientError, match=expected_error):
                        await client.submit_workflow_async(
                            workflow_id='title',
                            fields={'event_id': 'event-1'},
                            background=False,
                            session_id='event-1',
                        )
                finally:
                    await client.close()

        asyncio.run(exercise())

    def test_sync_submission_runs_from_a_worker_thread(self) -> None:
        async def exercise() -> dict[str, object]:
            async def submit(_request: Request) -> JSONResponse:
                return JSONResponse({'run_id': 'run-2'}, status_code=200)

            app = Starlette(
                routes=[Route('/workflows/title/runs', submit, methods=['POST'])]
            )
            client = AgentOSClient(
                app,
                service_token=_SERVICE_TOKEN,
                workflow_ids=frozenset({'title'}),
            )
            await client.start()
            try:
                return await asyncio.to_thread(
                    client.submit_workflow,
                    workflow_id='title',
                    fields={'session_id': 'session-1'},
                    background=False,
                    session_id='session-1',
                    timeout_seconds=1,
                )
            finally:
                await client.close()

        assert asyncio.run(exercise()) == {'run_id': 'run-2'}

    def test_sync_submission_rejects_calls_from_the_event_loop_thread(self) -> None:
        async def exercise() -> None:
            client = AgentOSClient(
                Starlette(),
                service_token=_SERVICE_TOKEN,
                workflow_ids=frozenset({'title'}),
            )
            await client.start()
            try:
                with pytest.raises(AgentOSClientError, match='worker thread'):
                    client.submit_workflow(
                        workflow_id='title',
                        fields={'session_id': 'session-1'},
                        background=False,
                        session_id='session-1',
                    )
            finally:
                await client.close()

        asyncio.run(exercise())

    def test_private_app_hides_unregistered_or_unauthorized_routes(self) -> None:
        forwarded_headers: list[dict[str, str]] = []

        async def submit(request: Request) -> JSONResponse:
            forwarded_headers.append(dict(request.headers.items()))
            return JSONResponse({'run_id': 'run-1'}, status_code=200)

        app = Starlette(
            routes=[Route('/workflows/title/runs', submit, methods=['POST'])]
        )
        private_app = PrivateAgentOSApp(
            app,
            service_token=_SERVICE_TOKEN,
            workflow_ids=frozenset({'title'}),
        )

        async def exercise() -> None:
            async with AsyncClient(
                transport=ASGITransport(app=private_app),
                base_url='http://agentos.internal',
            ) as client:
                unauthorized = await client.post(
                    '/workflows/title/runs',
                    headers={
                        'x-shifu-agentos-token': 'wrong-token',
                        'authorization': 'Bearer caller-token',
                    },
                )
                unregistered = await client.post(
                    '/workflows/other/runs',
                    headers={'x-shifu-agentos-token': _SERVICE_TOKEN},
                )
                wrong_method = await client.get(
                    '/workflows/title/runs',
                    headers={'x-shifu-agentos-token': _SERVICE_TOKEN},
                )
                invalid_prefix = await client.post(
                    '/not-workflows/title/runs',
                    headers={'x-shifu-agentos-token': _SERVICE_TOKEN},
                )
                invalid_suffix = await client.post(
                    '/workflows/title/runs/extra',
                    headers={'x-shifu-agentos-token': _SERVICE_TOKEN},
                )
                nested_workflow = await client.post(
                    '/workflows/nested/title/runs',
                    headers={'x-shifu-agentos-token': _SERVICE_TOKEN},
                )
                accepted = await client.post(
                    '/workflows/title/runs',
                    headers={
                        'x-shifu-agentos-token': _SERVICE_TOKEN,
                        'authorization': 'Bearer caller-token',
                    },
                )

            assert unauthorized.status_code == 404
            assert unregistered.status_code == 404
            assert wrong_method.status_code == 404
            assert invalid_prefix.status_code == 404
            assert invalid_suffix.status_code == 404
            assert nested_workflow.status_code == 404
            assert accepted.status_code == 200

        asyncio.run(exercise())
        assert len(forwarded_headers) == 1
        assert 'x-shifu-agentos-token' not in forwarded_headers[0]
        assert 'authorization' not in forwarded_headers[0]

    def test_sync_submission_fails_closed_without_a_running_client(self) -> None:
        client = AgentOSClient(
            Starlette(),
            service_token=_SERVICE_TOKEN,
            workflow_ids=frozenset({'title'}),
        )

        with pytest.raises(AgentOSClientError, match='not available'):
            client.submit_workflow(
                workflow_id='mentor-workflow',
                fields={'session_id': 'session-1'},
                background=False,
                session_id='session-1',
            )
