"""Docker-backed Inngest fixture for job integration tests."""

from collections.abc import Callable, Generator, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from threading import Thread
from typing import Any, cast
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session as SqlalchemySession
from testcontainers.core.container import DockerContainer
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer


@dataclass
class InngestFixture:
    process: subprocess.Popen[str]
    server_url: str
    inngest_url: str
    database_url: str
    mailpit_url: str
    bff_shared_secret: str
    output: list[str]
    inngest_container: DockerContainer | None = None
    output_reader: Thread | None = None

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

    def invoke_function(
        self,
        function_id: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        body = json.dumps(
            {
                'name': 'shifu/test-function-invocation',
                'data': payload or {},
            }
        ).encode()
        request = Request(  # noqa: S310 - local Inngest fixture URL
            f'{self.inngest_url}/invoke/{quote(function_id, safe="")}',
            data=body,
            headers={'content-type': 'application/json'},
            method='POST',
        )
        with urlopen(request, timeout=10) as response:  # noqa: S310
            if response.status not in {200, 201, 202}:
                raise AssertionError(
                    f'Inngest function invocation returned {response.status}'
                )

    def clear_application_tables(self) -> None:
        engine = create_engine(self.database_url, pool_pre_ping=True)
        try:
            _clear_application_tables(engine)
        finally:
            engine.dispose()

    @contextmanager
    def inspection_session(self) -> Generator[SqlalchemySession]:
        engine = create_engine(self.database_url, pool_pre_ping=True)
        try:
            with SqlalchemySession(engine) as session:
                yield session
        finally:
            engine.dispose()

    def clear_mailpit(self) -> None:
        request = Request(  # noqa: S310 - local Mailpit fixture URL
            f'{self.mailpit_url}/api/v1/messages',
            headers={'content-type': 'application/json'},
            method='DELETE',
        )
        with urlopen(request, timeout=10) as response:  # noqa: S310 - local Mailpit fixture URL
            if response.status not in {200, 204}:
                raise AssertionError(f'Mailpit cleanup returned {response.status}')

    def mailpit_messages(self) -> list[dict[str, object]]:
        with urlopen(  # noqa: S310 - local Mailpit fixture URL
            f'{self.mailpit_url}/api/v1/messages', timeout=10
        ) as response:
            raw_value: object = json.load(response)
        if not isinstance(raw_value, dict):
            return []
        payload = cast('dict[str, object]', raw_value)
        raw_messages: object = payload.get('messages')
        if not isinstance(raw_messages, list):
            return []
        messages = cast('list[object]', raw_messages)
        return [
            cast('dict[str, object]', message)
            for message in messages
            if isinstance(message, dict)
        ]

    def wait_for_mail(self, timeout: float = 90.0) -> list[dict[str, object]]:
        return self.wait_for_mail_count(1, timeout=timeout)

    def wait_for_mail_count(
        self,
        count: int,
        *,
        timeout: float = 30.0,
    ) -> list[dict[str, object]]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            messages = self.mailpit_messages()
            if len(messages) >= count:
                return messages
            time.sleep(0.1)
        raise AssertionError(
            f'Mailpit did not receive {count} message(s) before the timeout. '
            f'FastAPI output: {self.output[-100:]!r}; '
            f'Database: {self.database_diagnostics()}; '
            f'Inngest output: {self.inngest_diagnostics()}'
        )

    def wait_for_database(
        self,
        predicate: Callable[[SqlalchemySession], bool],
        *,
        timeout: float = 90.0,
    ) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.inspection_session() as session:
                if predicate(session):
                    return
            time.sleep(0.1)
        raise AssertionError(
            'Database predicate was not satisfied before the timeout. '
            f'FastAPI output: {self.output[-100:]!r}; '
            f'Database: {self.database_diagnostics()}; '
            f'Inngest output: {self.inngest_diagnostics()}'
        )

    def database_diagnostics(self) -> dict[str, object]:
        engine = create_engine(self.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                communications = (
                    connection.execute(
                        text(
                            'SELECT id, status, attempt_count, next_attempt_at, '
                            'failure_code FROM communication_messages'
                        )
                    )
                    .mappings()
                    .all()
                )
                events = (
                    connection.execute(
                        text(
                            'SELECT id, name, status, attempts, last_error_code '
                            'FROM events'
                        )
                    )
                    .mappings()
                    .all()
                )
            return {
                'communications': [dict(row) for row in communications],
                'events': [dict(row) for row in events],
            }
        finally:
            engine.dispose()

    def inngest_diagnostics(self) -> str:
        if self.inngest_container is None:
            return ''
        stdout, stderr = self.inngest_container.get_logs()
        return (stdout + stderr).decode(errors='replace')[-10000:]

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
        reader = self.output_reader
        if reader is not None:
            reader.join(timeout=5)
        self._drain_output()
        return ''.join(self.output)

    def start_output_reader(self) -> None:
        if self.output_reader is not None:
            return
        self.output_reader = Thread(
            target=self._read_output,
            name='shifu-inngest-test-output',
            daemon=True,
        )
        self.output_reader.start()

    def _read_output(self) -> None:
        stream = self.process.stdout
        if stream is None:
            return
        for line in stream:
            self.output.append(line)

    def _drain_output(self) -> None:
        if self.output_reader is not None:
            return
        stream = self.process.stdout
        if stream is None:
            return
        for line in stream:
            self.output.append(line)


@pytest.fixture(scope='session')
def _inngest_runtime() -> Iterator[InngestFixture]:
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
            mailpit = stack.enter_context(
                DockerContainer('axllent/mailpit:v1.21').with_exposed_ports(
                    1025,
                    8025,
                )
            )
            redis = stack.enter_context(RedisContainer('redis:7-alpine'))
        except Exception as error:  # noqa: BLE001 - Docker availability is an explicit skip.
            pytest.skip(f'Testcontainers runtime unavailable: {error}')

        inngest_host = inngest.get_container_host_ip()
        inngest_port = inngest.get_exposed_port(8288)
        inngest_url = f'http://{inngest_host}:{inngest_port}'
        mailpit_host = mailpit.get_container_host_ip()
        mailpit_smtp_port = mailpit.get_exposed_port(1025)
        mailpit_ui_port = mailpit.get_exposed_port(8025)
        mailpit_url = f'http://{mailpit_host}:{mailpit_ui_port}'
        bff_shared_secret = 'shifu-inngest-test-bff-secret'
        redis_host = redis.get_container_host_ip()
        redis_port = redis.get_exposed_port(6379)
        environment = os.environ.copy()
        environment.update(
            {
                'DATABASE_URL': postgres.get_connection_url(),
                'SHIFU_SERVER_APP_PORT': str(server_port),
                'INNGEST_BASE_URL': inngest_url,
                'INNGEST_DEV': '1',
                'INNGEST_EVENT_KEY': 'dev_key',
                'REDIS_URL': f'redis://{redis_host}:{redis_port}/0',
                'SHIFU_EMAIL_PROVIDER': 'smtp',
                'SHIFU_SMTP_HOST': mailpit_host,
                'SHIFU_SMTP_PORT': str(mailpit_smtp_port),
                'SHIFU_EMAIL_FROM': 'no-reply@shifu.local',
                'SHIFU_BFF_SHARED_SECRET': bff_shared_secret,
            }
        )
        subprocess.run(
            [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
            cwd=server_directory,
            env=environment,
            check=True,
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
        fixture = InngestFixture(
            process=process,
            server_url=server_url,
            inngest_url=inngest_url,
            database_url=postgres.get_connection_url(),
            mailpit_url=mailpit_url,
            bff_shared_secret=bff_shared_secret,
            output=[],
            inngest_container=inngest,
        )
        fixture.start_output_reader()
        _wait_for_url(f'{server_url}/health', timeout=30)
        _wait_for_url(f'{server_url}/api/inngest', timeout=30)
        _wait_for_url(f'{mailpit_url}/api/v1/messages', timeout=30)
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


@pytest.fixture
def inngest_fixture(
    _inngest_runtime: InngestFixture,
) -> Iterator[InngestFixture]:
    _inngest_runtime.clear_application_tables()
    _inngest_runtime.clear_mailpit()
    try:
        yield _inngest_runtime
    finally:
        _inngest_runtime.clear_application_tables()
        _inngest_runtime.clear_mailpit()


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(0.2)
        return connection.connect_ex((host, port)) == 0


def _clear_application_tables(engine: Engine) -> None:
    with engine.begin() as connection:
        table_names = connection.execute(
            text(
                'SELECT tablename FROM pg_tables '
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        ).scalars()
        quoted_table_names = ', '.join(
            f'"{table_name.replace(chr(34), chr(34) * 2)}"'
            for table_name in table_names
        )
        if quoted_table_names:
            connection.execute(
                text(f'TRUNCATE TABLE {quoted_table_names} RESTART IDENTITY CASCADE')
            )


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
