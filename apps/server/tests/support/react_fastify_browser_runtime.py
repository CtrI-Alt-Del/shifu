"""Task-owned disposable runtime. Never connects to a shared database.

Run from apps/server: uv run python -m tests.support.react_fastify_browser_runtime
The private env file is consumed by the Web dev process. Ctrl-C removes only
this process's API, inference endpoint, PostgreSQL and Redis containers.
"""

import json
import os
import secrets
import shlex
import socket
import subprocess
import sys
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import ClassVar, cast

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

_SERVER = Path(__file__).resolve().parents[2]
_LOGS = _SERVER.parent / 'web' / '.playwright-cli' / 'logs'


class _DecisionsHandler(BaseHTTPRequestHandler):
    """Real Jev wire protocol, deterministic choices, no submitted source logging."""

    mode: ClassVar[str] = 'complete'
    calls: ClassVar[int] = 0

    def log_message(self, format: str, *args: object) -> None:
        pass

    def do_POST(self) -> None:
        if self.path == '/mode':
            value = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            mode = value.decode()
            if mode not in {'complete', 'inconclusive', 'failure'}:
                self.send_error(400)
                return
            _DecisionsHandler.mode = mode
            self.send_response(204)
            self.end_headers()
            return
        if self.path != '/decisions':
            self.send_error(404)
            return
        _DecisionsHandler.calls += 1
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.mode == 'failure':
            self.send_error(503)
            return
        questions = cast('dict[str, dict[str, object]]', payload['questions'])
        choice = 'unknown' if self.mode == 'inconclusive' else 'comment-100'
        body = json.dumps(
            {
                'answers': {
                    key: {'type': 'choice', 'choice': choice} for key in questions
                }
            }
        ).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _require_free_ports() -> None:
    for port in (17790, 18790, 17090, 18791):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(('127.0.0.1', port))
            except OSError as error:
                raise RuntimeError(
                    f'Task port {port} is occupied; leave its owner running.'
                ) from error


def _migrate(database_url: str, agentos_url: str, environment: dict[str, str]) -> None:
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE ROLE shifu_agentos_runtime LOGIN PASSWORD 'agentos-test-password' "
                'NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT'
            )
            connection.exec_driver_sql(
                'GRANT CONNECT ON DATABASE shifu TO shifu_agentos_runtime'
            )
        subprocess.run(
            [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
            cwd=_SERVER,
            env=environment,
            check=True,
        )
    finally:
        engine.dispose()


def _seed(database_url: str, environment: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, '-m', 'shifu.shared.database.seed'],
        cwd=_SERVER,
        env=environment,
        check=True,
    )
    # Import settings-bound composition only after the isolated environment exists.
    from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
    from shifu.learning.core.domain.enums import SkillExperienceStatus
    from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
    from shifu.shared.database.seed_data import (
        SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
        SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID,
    )
    from tests.fixtures.react_fastify_activity_fixture import (
        ReactFastifyActivityFixture,
    )

    engine = create_engine(database_url)
    try:
        with SqlalchemyCurriculumDatabase(engine).transaction() as repositories:
            repositories.activities.add_many(
                [
                    ReactFastifyActivityFixture.activity(),
                    ReactFastifyActivityFixture.activity(
                        integrated_last=False,
                        activity_id=ReactFastifyActivityFixture.SECOND_ACTIVITY_ID,
                    ),
                ]
            )
        with SqlalchemyLearningDatabase(engine).transaction() as repositories:
            experience = repositories.skill_experiences.find_by_id(
                SEED_ADAPTIVE_LAB_EXPERIENCE_ID
            )
            assert experience is not None
            experience.status = SkillExperienceStatus.LEARNING
            repositories.skill_experiences.update(experience)
            progress = repositories.competency_progresses.find_by_id(
                SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID
            )
            assert progress is not None
            progress.content_released = True
            repositories.competency_progresses.update(progress)
        path = ReactFastifyActivityFixture.activity_path()
        (_LOGS / 'shifu90-scenario.json').write_text(
            json.dumps(
                {
                    'activity_path': path,
                    'second_activity_path': path.replace(
                        ReactFastifyActivityFixture.ACTIVITY_ID,
                        ReactFastifyActivityFixture.SECOND_ACTIVITY_ID,
                    ),
                    'task_attempts_initial': 0,
                    'inference_mode_endpoint': 'http://127.0.0.1:18790/mode',
                },
                indent=2,
            )
        )
    finally:
        engine.dispose()


def main() -> None:
    _require_free_ports()
    _LOGS.mkdir(parents=True, exist_ok=True)
    with ExitStack() as resources:
        postgres = resources.enter_context(
            PostgresContainer(
                'pgvector/pgvector:0.8.1-pg17',
                username='shifu',
                password=secrets.token_hex(16),
                dbname='shifu',
                driver='psycopg',
            )
        )
        redis = resources.enter_context(RedisContainer('redis:7-alpine'))
        database_url = postgres.get_connection_url()
        agentos_url = (
            make_url(database_url)
            .set(
                username='shifu_agentos_runtime',
                password='agentos-test-password',  # noqa: S106 - Disposable runtime credential.
            )
            .render_as_string(hide_password=False)
        )
        environment = os.environ.copy()
        environment.update(
            {
                'DATABASE_URL': database_url,
                'AGENTOS_DATABASE_URL': agentos_url,
                'REDIS_URL': f'redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0',
                'SHIFU_SERVER_APP_MODE': 'local',
                'SHIFU_SERVER_APP_PORT': '17790',
                'SHIFU_AUTH_ISSUER': 'http://127.0.0.1:17090',
                'SHIFU_AUTH_JWKS_URL': 'http://127.0.0.1:17090/api/auth/jwks',
                'SHIFU_COMMUNICATION_ENCRYPTION_KEYS': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
                'OPENROUTER_API_KEY': 'disposable-local-inference',
                'OPENROUTER_DECISIONS_URL': 'http://127.0.0.1:18790/decisions',
                'MENTOR_TELEMETRY_ENABLED': 'false',
                'INNGEST_APP_ID': 'shifu90-disposable',
                'INNGEST_BASE_URL': 'http://127.0.0.1:18791',
                'INNGEST_API_BASE_URL': 'http://127.0.0.1:18791',
                'INNGEST_EVENT_API_BASE_URL': 'http://127.0.0.1:18791',
                'BETTER_AUTH_DATABASE_URL': database_url.replace('+psycopg', ''),
                'BETTER_AUTH_SECRET': secrets.token_hex(32),
                'SHIFU_BFF_SHARED_SECRET': secrets.token_hex(32),
                'SHIFU_WEB_APP_URL': 'http://127.0.0.1:17090',
                'SHIFU_WEB_APP_PORT': '17090',
                'SHIFU_WEB_APP_MODE': 'local',
                'SHIFU_IDENTITY_API_URL': 'http://127.0.0.1:17790',
                'VITE_SHIFU_SERVER_URL': 'http://127.0.0.1:17790',
            }
        )
        _migrate(database_url, agentos_url, environment)
        os.environ.update(environment)
        _seed(database_url, environment)
        exported = {
            key: value
            for key, value in environment.items()
            if key
            in {
                'DATABASE_URL',
                'AGENTOS_DATABASE_URL',
                'REDIS_URL',
                'BETTER_AUTH_DATABASE_URL',
                'BETTER_AUTH_SECRET',
                'SHIFU_BFF_SHARED_SECRET',
                'SHIFU_WEB_APP_URL',
                'SHIFU_WEB_APP_PORT',
                'SHIFU_WEB_APP_MODE',
                'SHIFU_IDENTITY_API_URL',
                'VITE_SHIFU_SERVER_URL',
            }
        }
        env_path = _LOGS / 'shifu90-runtime.env'
        env_path.touch(mode=0o600)
        env_path.chmod(0o600)
        env_path.write_text(
            ''.join(
                f'export {key}={shlex.quote(value)}\n'
                for key, value in exported.items()
            )
        )
        endpoint = ThreadingHTTPServer(('127.0.0.1', 18790), _DecisionsHandler)
        resources.callback(endpoint.server_close)
        thread = Thread(target=endpoint.serve_forever, daemon=True)
        thread.start()
        resources.callback(endpoint.shutdown)
        log = resources.enter_context((_LOGS / 'shifu90-api.log').open('w'))
        api = subprocess.Popen(
            [
                sys.executable,
                '-m',
                'uvicorn',
                'main:app',
                '--host',
                '127.0.0.1',
                '--port',
                '17790',
            ],
            cwd=_SERVER,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            print(
                'Disposable API 17790, inference 18790. Private Web env and scenario under .playwright-cli/logs.',
                flush=True,
            )
            api.wait()
        except KeyboardInterrupt:
            pass
        finally:
            api.terminate()
            try:
                api.wait(timeout=15)
            except subprocess.TimeoutExpired:
                api.kill()
                api.wait()
            env_path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
