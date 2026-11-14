"""Private, allowlisted ASGI client for one module-owned AgentOS app."""

from __future__ import annotations

import asyncio
import hmac
import json
import re
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError
from threading import get_ident
from typing import TYPE_CHECKING, cast

import httpx

if TYPE_CHECKING:
    from collections.abc import Mapping

    from starlette.types import ASGIApp, Receive, Scope, Send


_SAFE_FIELD_NAMES = frozenset(
    {
        'handoff_ref',
        'event_id',
        'event_name',
        'attempt_id',
        'run_id',
        'skill_experience_id',
        'activity_id',
        'kind',
        'requested_at',
        'attachment_id',
        'generation',
        'batch_id',
        'deletion_generation',
        'account_id',
        'session_id',
        'message_id',
        'planning_id',
        'operation_id',
    }
)
_SAFE_VALUE = re.compile(r'^[A-Za-z0-9_.:/+-]{1,160}$')


class AgentOSClientError(RuntimeError):
    """A private workflow request failed without exposing response content."""


class PrivateAgentOSApp:
    """Filter native AgentOS routes and require an in-process service token."""

    _TOKEN_HEADER = b'x-shifu-agentos-token'

    def __init__(
        self,
        app: ASGIApp,
        *,
        service_token: str,
        workflow_ids: frozenset[str],
    ) -> None:
        self._app = app
        self._service_token = service_token.encode('utf-8')
        self._workflow_ids = workflow_ids

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get('type') != 'http':
            await self._not_found(scope, receive, send)
            return
        path = str(scope.get('path', ''))
        method = scope.get('method')
        workflow_id = self._workflow_for_path(path)
        if method != 'POST' or workflow_id is None:
            await self._not_found(scope, receive, send)
            return

        headers = cast('list[tuple[bytes, bytes]]', scope.get('headers', []))
        supplied = next(
            (value for name, value in headers if name.lower() == self._TOKEN_HEADER),
            b'',
        )
        if not hmac.compare_digest(supplied, self._service_token):
            await self._not_found(scope, receive, send)
            return

        private_scope = dict(scope)
        private_scope['headers'] = [
            (name, value)
            for name, value in headers
            if name.lower() != self._TOKEN_HEADER and name.lower() != b'authorization'
        ]
        await self._app(private_scope, receive, send)

    def _workflow_for_path(self, path: str) -> str | None:
        prefix = '/workflows/'
        suffix = '/runs'
        if not path.startswith(prefix) or not path.endswith(suffix):
            return None
        workflow_id = path[len(prefix) : -len(suffix)]
        if not workflow_id or '/' in workflow_id:
            return None
        return workflow_id if workflow_id in self._workflow_ids else None

    @staticmethod
    async def _not_found(scope: Scope, receive: Receive, send: Send) -> None:
        body = b'{"detail":"Not Found"}'
        await send(
            {
                'type': 'http.response.start',
                'status': 404,
                'headers': [
                    (b'content-type', b'application/json'),
                    (b'content-length', str(len(body)).encode('ascii')),
                    (b'cache-control', b'no-store'),
                ],
            }
        )
        await send({'type': 'http.response.body', 'body': body})


class AgentOSClient:
    """Submit only safe workflow envelopes to the private module app."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        service_token: str,
        workflow_ids: frozenset[str],
    ) -> None:
        self._private_app = PrivateAgentOSApp(
            app,
            service_token=service_token,
            workflow_ids=workflow_ids,
        )
        self._service_token = service_token
        self._workflow_ids = workflow_ids
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread_id: int | None = None
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._client is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._loop_thread_id = get_ident()
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self._private_app),
            base_url='http://agentos.internal',
            timeout=610.0,
        )

    async def close(self) -> None:
        client = self._client
        self._client = None
        self._loop = None
        self._loop_thread_id = None
        if client is not None:
            await client.aclose()

    def submit_workflow(
        self,
        *,
        workflow_id: str,
        fields: Mapping[str, str],
        background: bool,
        session_id: str,
        timeout_seconds: float = 610.0,
    ) -> dict[str, object]:
        loop = self._loop
        if loop is None or self._client is None or loop.is_closed():
            raise AgentOSClientError('AgentOS is not available')
        if get_ident() == self._loop_thread_id:
            raise AgentOSClientError(
                'Synchronous AgentOS calls require a worker thread'
            )
        message = self._serialize_fields(fields)
        future: Future[dict[str, object]] = asyncio.run_coroutine_threadsafe(
            self._submit_async(
                workflow_id=workflow_id,
                message=message,
                background=background,
                session_id=self._safe_value('session_id', session_id),
                timeout_seconds=timeout_seconds,
            ),
            loop,
        )
        try:
            return future.result(timeout=timeout_seconds + 2)
        except FutureTimeoutError as error:
            future.cancel()
            raise AgentOSClientError('AgentOS request timed out') from error
        except Exception as error:
            if isinstance(error, AgentOSClientError):
                raise
            raise AgentOSClientError('AgentOS request failed') from error

    async def submit_workflow_async(
        self,
        *,
        workflow_id: str,
        fields: Mapping[str, str],
        background: bool,
        session_id: str,
        timeout_seconds: float = 610.0,
    ) -> dict[str, object]:
        return await self._submit_async(
            workflow_id=workflow_id,
            message=self._serialize_fields(fields),
            background=background,
            session_id=self._safe_value('session_id', session_id),
            timeout_seconds=timeout_seconds,
        )

    async def _submit_async(
        self,
        *,
        workflow_id: str,
        message: str,
        background: bool,
        session_id: str,
        timeout_seconds: float,
    ) -> dict[str, object]:
        if workflow_id not in self._workflow_ids:
            raise AgentOSClientError('Workflow is not registered')
        client = self._client
        if client is None:
            raise AgentOSClientError('AgentOS is not available')
        try:
            response = await client.post(
                f'/workflows/{workflow_id}/runs',
                data={
                    'message': message,
                    'background': 'true' if background else 'false',
                    'stream': 'false',
                    'session_id': session_id,
                    'user_id': 'shifu-internal',
                },
                headers={'x-shifu-agentos-token': self._service_token},
                timeout=timeout_seconds,
            )
        except Exception as error:
            raise AgentOSClientError('AgentOS request failed') from error
        else:
            return self._validated_receipt(response, background=background)

    @staticmethod
    def _validated_receipt(
        response: httpx.Response, *, background: bool
    ) -> dict[str, object]:
        try:
            response.raise_for_status()
            body = response.json()
        except Exception as error:
            raise AgentOSClientError('AgentOS request failed') from error
        if not isinstance(body, dict):
            raise AgentOSClientError('AgentOS returned an invalid response')
        result = cast('dict[str, object]', body)
        if background and (
            response.status_code != 202 or result.get('status') != 'PENDING'
        ):
            raise AgentOSClientError('AgentOS did not durably admit the run')
        return result

    @classmethod
    def _serialize_fields(cls, fields: Mapping[str, str]) -> str:
        if not fields or len(fields) > len(_SAFE_FIELD_NAMES):
            raise AgentOSClientError('Workflow envelope is invalid')
        safe: dict[str, str] = {}
        for key, value in fields.items():
            if key not in _SAFE_FIELD_NAMES:
                raise AgentOSClientError('Workflow envelope is invalid')
            safe[key] = cls._safe_value(key, value)
        return json.dumps(safe, separators=(',', ':'), sort_keys=True)

    @staticmethod
    def _safe_value(key: str, value: str) -> str:
        if _SAFE_VALUE.fullmatch(value) is None:
            raise AgentOSClientError('Workflow envelope is invalid')
        if key == 'kind' and value not in {'learning', 'diagnostic', 'review'}:
            raise AgentOSClientError('Workflow envelope is invalid')
        return value
