"""Loopback-only deterministic Decisions stub for the React browser fixture.

Run from ``apps/server`` with::

    python devtools/react_browser_fixture/decisions_stub.py

Set ``SHIFU_REACT_FIXTURE_DECISIONS_PORT`` to change the default port (18779).
Point ``OPENROUTER_DECISIONS_URL`` at
``http://127.0.0.1:<port>/api/alpha/decisions`` and set any non-empty local
``OPENROUTER_API_KEY``. This server never contacts an external service and
never logs request bodies or learner source.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from typing import cast

_DEFAULT_PORT = 18779
_MAX_REQUEST_BYTES = 1_000_000
_DECISIONS_PATH = '/api/alpha/decisions'


def _configured_port() -> int:
    raw_port = os.environ.get('SHIFU_REACT_FIXTURE_DECISIONS_PORT')
    if raw_port is None:
        return _DEFAULT_PORT

    try:
        port = int(raw_port)
    except ValueError as error:
        raise SystemExit(
            'SHIFU_REACT_FIXTURE_DECISIONS_PORT must be an integer from 1 to 65535'
        ) from error

    if not 1 <= port <= 65535:
        raise SystemExit(
            'SHIFU_REACT_FIXTURE_DECISIONS_PORT must be an integer from 1 to 65535'
        )
    return port


class _DecisionsHandler(BaseHTTPRequestHandler):
    request_count = 0

    def do_GET(self) -> None:
        if self.path != '/health':
            self._send_json(404, {'error': 'not found'})
            return
        self._send_json(200, {'status': 'ok'})

    def do_POST(self) -> None:
        type(self).request_count += 1
        status = 400
        try:
            if self.path != _DECISIONS_PATH:
                status = 404
                self._send_json(status, {'error': 'not found'})
                return

            length = self.headers.get('Content-Length')
            if length is None:
                self._send_json(status, {'error': 'content length required'})
                return

            try:
                body_size = int(length)
            except ValueError:
                self._send_json(status, {'error': 'invalid content length'})
                return

            if not 0 <= body_size <= _MAX_REQUEST_BYTES:
                status = 413
                self._send_json(status, {'error': 'request too large'})
                return

            try:
                payload = json.loads(self.rfile.read(body_size))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(status, {'error': 'invalid JSON'})
                return

            questions = self._questions_from(payload)
            if questions is None:
                self._send_json(status, {'error': 'invalid Decisions request'})
                return

            answers = {
                question_id: {
                    'type': 'choice',
                    'choice': self._deterministic_choice(criteria),
                }
                for question_id, criteria in questions.items()
            }
            status = 200
            self._send_json(status, {'answers': answers})
        finally:
            # Keep diagnostics useful while ensuring prompts and source stay private.
            print(f'request={type(self).request_count} status={status}', flush=True)

    @staticmethod
    def _questions_from(payload: object) -> dict[str, dict[str, str]] | None:
        if not isinstance(payload, dict):
            return None
        payload = cast('dict[str, object]', payload)

        questions = payload.get('questions')
        state = payload.get('state')
        if (
            not isinstance(questions, dict)
            or not questions
            or not isinstance(state, dict)
        ):
            return None
        questions = cast('dict[object, object]', questions)
        state = cast('dict[str, object]', state)

        if not all(
            isinstance(state.get(field), expected_type)
            for field, expected_type in (
                ('question_kind', str),
                ('prompt', str),
                ('project_files', list),
                ('submitted_paths', list),
            )
        ):
            return None

        valid_questions: dict[str, dict[str, str]] = {}
        for question_id, question in questions.items():
            if not isinstance(question_id, str) or not isinstance(question, dict):
                return None
            question = cast('dict[str, object]', question)
            if question.get('type') != 'choice' or not isinstance(
                question.get('instructions'), str
            ):
                return None
            criteria = question.get('criteria')
            if not isinstance(criteria, dict) or not criteria:
                return None
            criteria = cast('dict[object, object]', criteria)
            if not all(
                isinstance(option_id, str) and isinstance(description, str)
                for option_id, description in criteria.items()
            ):
                return None
            valid_questions[question_id] = cast('dict[str, str]', criteria)
        return valid_questions

    @staticmethod
    def _deterministic_choice(criteria: dict[str, str]) -> str:
        return next(
            (option_id for option_id in criteria if option_id.endswith('75')),
            next(iter(criteria)),
        )

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        # BaseHTTPRequestHandler's default log includes request targets.
        del format, args


def main() -> None:
    server = ThreadingHTTPServer(('127.0.0.1', _configured_port()), _DecisionsHandler)
    print(
        f'Decisions stub listening on http://127.0.0.1:{server.server_port}; '
        'press Ctrl+C to stop',
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Decisions stub stopping', flush=True)
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
