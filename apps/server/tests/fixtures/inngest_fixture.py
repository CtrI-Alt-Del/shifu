"""Docker-backed Inngest fixture for job integration tests."""

from collections.abc import Iterator
from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.community.postgres import PostgresContainer


@dataclass
class InngestFixture:
    process: subprocess.Popen[str]
    inngest_url: str
    output: list[str]

    def publish(
        self, event_name: str, payload: dict[str, object], event_id: str
    ) -> None:
        body = json.dumps(
            {
                'name': event_name,
                'data': payload,
                'id': event_id,
                'ts': int(time.time() * 1000),
            }
        ).encode()
        request = Request(  # noqa: S310 - local HTTP fixture URL
            f'{self.inngest_url}/e/dev_key',
            data=body,
            headers={'content-type': 'application/json'},
            method='POST',
        )
        with urlopen(request, timeout=10) as response:  # noqa: S310 - local HTTP fixture URL
            if response.status not in {200, 201, 202}:
                raise AssertionError(
                    f'Inngest event submission returned {response.status}'
                )

    def wait_for_log(self, text: str, timeout: float = 30.0) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._drain_output()
            matching = next((line for line in self.output if text in line), None)
            if matching is not None:
                return matching
            time.sleep(0.1)
        raise AssertionError(
            f'Inngest job did not emit {text!r} before the bounded timeout. '
            f'Captured output: {self.output!r}'
        )

    def close(self) -> str:
        self._drain_output()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self._drain_output()
        return ''.join(self.output)

    def _drain_output(self) -> None:
        stream = self.process.stdout
        if stream is None:
            return
        while select.select([stream], [], [], 0)[0]:
            line = stream.readline()
            if not line:
                break
            self.output.append(line)


@pytest.fixture(scope='session')
def inngest_fixture() -> Iterator[InngestFixture]:
    if os.environ.get('SHIFU_RUN_REAL_INNGEST_TESTS') != '1':
        pytest.skip('set SHIFU_RUN_REAL_INNGEST_TESTS=1 to run Docker-backed job tests')

    server_port = int(os.environ.get('SHIFU_INNGEST_FASTAPI_PORT', '7777'))
    server_url = f'http://127.0.0.1:{server_port}'
    if _port_is_open('127.0.0.1', server_port):
        pytest.skip(
            f'FastAPI port {server_port} is already occupied; Inngest fixture needs ownership'
        )

    server_directory = Path(__file__).parents[2]
    process: subprocess.Popen[str] | None = None
    fixture: InngestFixture | None = None
    stack = ExitStack()
    try:
        try:
            postgres = stack.enter_context(
                PostgresContainer(
                    'postgres:17-alpine',
                    username='shifu',
                    password='change-me',  # noqa: S106 - disposable test credential
                    dbname='shifu',
                    driver='psycopg',
                )
            )
            inngest = stack.enter_context(
                DockerContainer('inngest/inngest:v1.41.1')
                .with_exposed_ports(8288)
                .with_command(
                    'inngest dev '
                    f'-u http://host.docker.internal:{server_port}/api/inngest '
                    '--host 0.0.0.0 --port 8288 '
                    '--connect-gateway-port 8289 --no-discovery --persist'
                )
                .with_kwargs(extra_hosts={'host.docker.internal': 'host-gateway'})
            )
        except Exception as error:  # noqa: BLE001 - Docker availability is an explicit skip.
            pytest.skip(f'Testcontainers runtime unavailable: {error}')

        inngest_host = inngest.get_container_host_ip()
        inngest_port = inngest.get_exposed_port(8288)
        inngest_url = f'http://{inngest_host}:{inngest_port}'
        environment = os.environ.copy()
        environment.update(
            {
                'DATABASE_URL': postgres.get_connection_url(),
                'SHIFU_SERVER_APP_PORT': str(server_port),
                'INNGEST_BASE_URL': inngest_url,
                'INNGEST_DEV': '1',
            }
        )
        process = subprocess.Popen(  # noqa: S603 - fixed local test command
            [
                sys.executable,
                '-m',
                'uvicorn',
                'main:app',
                '--app-dir',
                'src',
                '--host',
                '0.0.0.0',  # noqa: S104 - the Docker runtime must reach this host process.
                '--port',
                str(server_port),
            ],
            cwd=server_directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        fixture = InngestFixture(process, inngest_url, [])
        _wait_for_url(f'{server_url}/health', timeout=30)
        _wait_for_url(f'{server_url}/api/inngest', timeout=30)
        _wait_for_inngest_app(
            inngest_url,
            app_id=environment.get('INNGEST_APP_ID', 'shifu'),
            timeout=30,
        )
        yield fixture
    finally:
        if fixture is not None:
            fixture.close()
        elif process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        stack.close()


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(0.2)
        return connection.connect_ex((host, port)) == 0


def _wait_for_url(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Any = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2):  # noqa: S310 - local HTTP fixture URL
                return
        except (OSError, URLError) as error:
            last_error = error
            time.sleep(0.2)
    raise AssertionError(
        f'URL was not ready before timeout: {url}; last error: {last_error}'
    )


def _wait_for_inngest_app(inngest_url: str, app_id: str, timeout: float) -> None:
    """Wait until the Dev Server has accepted the app's function registration."""

    query = {'query': ('query GetApps { apps { name connected functionCount } }')}
    request_body = json.dumps(query).encode()
    deadline = time.monotonic() + timeout
    last_error: Any = None
    while time.monotonic() < deadline:
        try:
            request = Request(  # noqa: S310 - local Inngest fixture URL
                f'{inngest_url}/v0/gql',
                data=request_body,
                headers={'content-type': 'application/json'},
                method='POST',
            )
            with urlopen(request, timeout=2) as response:  # noqa: S310
                result = json.load(response)
            apps = result.get('data', {}).get('apps', [])
            if any(
                app.get('name') == app_id
                and app.get('connected') is True
                and app.get('functionCount', 0) > 0
                for app in apps
            ):
                return
            last_error = f'Inngest app {app_id!r} is not connected: {apps!r}'
        except (OSError, URLError, ValueError, AttributeError) as error:
            last_error = error
        time.sleep(0.2)
    raise AssertionError(
        f'Inngest app was not registered before timeout: {app_id}; '
        f'last error: {last_error}'
    )
