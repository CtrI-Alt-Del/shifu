import json
import logging
import re
import sys
import traceback
from collections.abc import Mapping
from datetime import UTC, datetime
from math import isfinite
from typing import ClassVar, TextIO, cast
from uuid import UUID

from shifu.shared.core.interfaces.telemetry_provider import (
    SanitizedStackFrame,
    TelemetryEnvironment,
    TelemetryEventInput,
    TelemetryLevel,
    TelemetryProvider,
    TelemetryService,
)


_LOG_LEVEL_BY_NAME = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
}
_telemetry_log_handler: 'TelemetryLoggingHandler | None' = None


_SAFE_ID_PATTERN = re.compile(r'^[A-Za-z0-9._:-]{1,128}$')
_SAFE_METHOD_PATTERN = re.compile(r'^[A-Z]{3,10}$')
_SAFE_EXCEPTION_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]{0,127}$')
_SAFE_FILE_PATTERN = re.compile(r'^[A-Za-z0-9_.-]{1,255}$')
_SAFE_FUNCTION_PATTERN = re.compile(r'^[A-Za-z_<>][A-Za-z0-9_<>.:-]{0,127}$')
_SAFE_ROUTE_SEGMENT_PATTERN = re.compile(r'^[A-Za-z_-][A-Za-z0-9_.~-]*$')
_ROUTE_PARAMETER_PATTERN = re.compile(r'^\{[A-Za-z_][A-Za-z0-9_]*\}$')
_UUID_PATTERN = re.compile(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-'
    r'[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'
)
_MAX_STACK_FRAMES = 20
_NOISY_LOGGERS = ('httpx', 'httpx2', 'httpcore', 'httpcore2')


class ConsoleTelemetryProvider(TelemetryProvider):
    """Serialize the fixed telemetry contract to one deterministic JSON line."""

    _LEVEL_RANK: ClassVar[dict[str, int]] = {
        'DEBUG': 10,
        'INFO': 20,
        'WARNING': 30,
        'ERROR': 40,
    }
    _EVENT_MESSAGES: ClassVar[dict[str, str]] = {
        'http.request.completed': 'HTTP request completed',
        'http.request.failed': 'HTTP request failed',
        'error.unexpected': 'Unexpected error',
        'auth.login.succeeded': 'Authentication succeeded',
        'auth.login.refused': 'Authentication refused',
        'auth.session.revoked': 'Session revoked',
        'auth.access.denied': 'Access denied',
        'learning.goal.created': 'Learning goal created',
        'learning.goal.deleted': 'Learning goal deleted',
        'learning.attempt.submitted': 'Learning attempt submitted',
        'learning.evaluation.completed': 'Learning evaluation completed',
        'job.started': 'Job started',
        'job.completed': 'Job completed',
        'job.failed': 'Job failed',
        'job.retrying': 'Job retrying',
        'integration.operation.started': 'Integration operation started',
        'integration.operation.completed': 'Integration operation completed',
        'integration.operation.failed': 'Integration operation failed',
        'integration.operation.retrying': 'Integration operation retrying',
        'app.startup.completed': 'Application startup completed',
        'app.shutdown.completed': 'Application shutdown completed',
        'app.version.reported': 'Application version reported',
        'dependency.unavailable': 'Dependency unavailable',
    }
    _OPERATIONS: ClassVar[frozenset[str]] = frozenset(
        {
            'http.request',
            'auth.login',
            'auth.session.revoke',
            'auth.access',
            'goal.create',
            'goal.delete',
            'attempt.submit',
            'evaluation.complete',
            'app.startup',
            'app.shutdown',
            'dependency.check',
            'inngest.dispatch',
            'resend.send',
            'openrouter.generate',
        }
    )
    _JOBS: ClassVar[frozenset[str]] = frozenset(
        {
            'gamification.recognize_skill_completed',
            'gamification.recognize_practice_day_on_diagnostic_completed',
            'gamification.recognize_practice_day_on_activity_evaluated',
            'gamification.recognize_diagnostic_completed',
            'gamification.recognize_competency_mastered',
            'gamification.purge_profile_on_account_deleted',
            'gamification.create_profile_on_account_activated',
            'communication.cancel_communication',
            'communication.deliver_communication',
            'learning.evaluate_choice_activity',
            'intelligence.purge_mentor_attachments_on_account_deleted',
            'intelligence.purge_mentor_summaries_on_account_deleted',
            'intelligence.purge_learner_memories_on_account_deleted',
            'intelligence.purge_mentor_action_proposals_on_account_deleted',
            'intelligence.record_mentor_action_outcome',
            'identity.record_communication_delivery_state',
            'identity.log_main_page_entered',
            'identity.fan_out_unconfirmed_account_expiry',
            'identity.expire_unconfirmed_account',
        }
    )
    _INTEGRATIONS: ClassVar[frozenset[str]] = frozenset(
        {'inngest', 'resend', 'openrouter'}
    )
    _DEPENDENCIES: ClassVar[frozenset[str]] = frozenset(
        {'database', 'inngest', 'resend', 'openrouter', 'better-auth'}
    )
    _RESULTS: ClassVar[frozenset[str]] = frozenset(
        {'success', 'failure', 'retry', 'unavailable'}
    )
    _ERROR_CODES: ClassVar[frozenset[str]] = frozenset(
        {
            'invalid_credentials',
            'identity_unavailable',
            'service_unavailable',
            'invalid_input',
            'bad_request',
            'unauthorized',
            'forbidden',
            'not_found',
            'conflict',
            'method_not_allowed',
            'content_too_large',
            'unsupported_media_type',
            'validation_error',
            'rate_limited',
            'request_failed',
            'internal_error',
            'job_failed',
            'integration_unavailable',
            'integration_failed',
        }
    )

    def __init__(
        self,
        *,
        service: TelemetryService,
        environment: TelemetryEnvironment,
        version: str,
        log_level: TelemetryLevel = 'INFO',
        stream: TextIO | None = None,
    ) -> None:
        self._service: TelemetryService = service
        self._environment: TelemetryEnvironment = environment
        self._version: str = version.strip() or 'local-dev'
        self._log_level: TelemetryLevel = log_level
        self._stream: TextIO = stream or sys.stdout

    def emit(self, event: TelemetryEventInput) -> None:
        """Emit a filtered event without ever affecting the caller."""
        try:
            level = event.get('level')
            event_name = event.get('event')
            if event_name not in self._EVENT_MESSAGES:
                return
            if level not in self._LEVEL_RANK:
                return
            if self._LEVEL_RANK[level] < self._LEVEL_RANK[self._log_level]:
                return

            record = self._build_record(event, level, event_name)
            serialized = json.dumps(
                record,
                ensure_ascii=False,
                separators=(',', ':'),
                sort_keys=True,
            )
            self._stream.write(f'{serialized}\n')
            self._stream.flush()
        except Exception:  # noqa: BLE001 - telemetry is best effort by contract.
            return

    def _build_record(
        self,
        event: TelemetryEventInput,
        level: str,
        event_name: str,
    ) -> dict[str, object]:
        record: dict[str, object] = {
            'timestamp': datetime.now(tz=UTC).isoformat().replace('+00:00', 'Z'),
            'level': level,
            'service': self._service,
            'environment': self._environment,
            'version': self._version,
            'event': event_name,
            'message': self._EVENT_MESSAGES[event_name],
        }
        self._add_ids(record, event)
        self._add_request_fields(record, event)
        self._add_catalog_fields(record, event)
        return record

    @classmethod
    def _add_ids(
        cls,
        record: dict[str, object],
        event: TelemetryEventInput,
    ) -> None:
        request_id = event.get('request_id')
        if cls._is_uuid_v4(request_id):
            record['request_id'] = request_id
        for name in ('run_id', 'event_id'):
            value = event.get(name)
            if isinstance(value, str) and _SAFE_ID_PATTERN.fullmatch(value):
                record[name] = value

    @classmethod
    def _add_request_fields(
        cls,
        record: dict[str, object],
        event: TelemetryEventInput,
    ) -> None:
        method = event.get('method')
        if isinstance(method, str) and _SAFE_METHOD_PATTERN.fullmatch(method):
            record['method'] = method

        route = event.get('route')
        if isinstance(route, str) and cls._is_safe_route(route):
            record['route'] = route

        status_code = event.get('status_code')
        if type(status_code) is int and 100 <= status_code <= 599:
            record['status_code'] = status_code

        duration_ms = event.get('duration_ms')
        if (
            isinstance(duration_ms, (int, float))
            and not isinstance(duration_ms, bool)
            and isfinite(duration_ms)
            and duration_ms >= 0
        ):
            record['duration_ms'] = float(duration_ms)

    @classmethod
    def _add_catalog_fields(
        cls,
        record: dict[str, object],
        event: TelemetryEventInput,
    ) -> None:
        for name, allowed in (
            ('operation', cls._OPERATIONS),
            ('job', cls._JOBS),
            ('integration', cls._INTEGRATIONS),
            ('dependency', cls._DEPENDENCIES),
            ('result', cls._RESULTS),
            ('error_code', cls._ERROR_CODES),
        ):
            value = event.get(name)
            if isinstance(value, str) and value in allowed:
                record[name] = value

        attempt = event.get('attempt')
        if type(attempt) is int and attempt >= 1:
            record['attempt'] = attempt

        exception_type = event.get('exception_type')
        if isinstance(exception_type, str) and _SAFE_EXCEPTION_PATTERN.fullmatch(
            exception_type
        ):
            record['exception_type'] = exception_type

        stack_trace = cls.sanitize_stack_trace(event.get('stack_trace'))
        if stack_trace:
            record['stack_trace'] = stack_trace

    @staticmethod
    def _is_uuid_v4(value: object) -> bool:
        if not isinstance(value, str):
            return False
        try:
            return UUID(value).version == 4
        except ValueError:
            return False

    @staticmethod
    def _is_safe_route(value: str) -> bool:
        route = value.strip()
        if route == 'unmatched':
            return True
        if not route.startswith('/') or len(route) > 256 or '?' in route:
            return False
        segments = route.split('/')[1:]
        if any(not segment for segment in segments):
            return False
        for segment in segments:
            if _ROUTE_PARAMETER_PATTERN.fullmatch(segment):
                continue
            if not _SAFE_ROUTE_SEGMENT_PATTERN.fullmatch(segment):
                return False
            if segment.isdigit() or _UUID_PATTERN.fullmatch(segment):
                return False
            if len(segment) >= 16 and segment.isalnum():
                return False
        return True

    @staticmethod
    def sanitize_stack_trace(value: object) -> list[SanitizedStackFrame]:
        if not isinstance(value, list):
            return []
        sanitized: list[SanitizedStackFrame] = []
        for item in cast('list[object]', value[:_MAX_STACK_FRAMES]):
            if not isinstance(item, Mapping):
                continue
            frame = cast('Mapping[str, object]', item)
            raw_file = frame.get('file')
            if not isinstance(raw_file, str) or not raw_file.strip():
                continue
            file_name = raw_file.replace('\\', '/').rsplit('/', 1)[-1]
            if not file_name or file_name in {'.', '..'}:
                continue
            file_name = file_name[:255]
            if not _SAFE_FILE_PATTERN.fullmatch(file_name):
                continue
            safe_frame: SanitizedStackFrame = {'file': file_name}
            line = frame.get('line')
            if type(line) is int and line >= 1:
                safe_frame['line'] = line
            function = frame.get('function')
            if isinstance(function, str) and _SAFE_FUNCTION_PATTERN.fullmatch(function):
                safe_frame['function'] = function
            sanitized.append(safe_frame)
        return sanitized


class TelemetryLoggingHandler(logging.Handler):
    """Adapt framework records to the fixed telemetry contract without messages."""

    def __init__(self, provider: TelemetryProvider) -> None:
        super().__init__(level=logging.NOTSET)
        self.provider = provider

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.name.startswith('uvicorn.access'):
                return

            if record.levelno < logging.WARNING:
                return

            exception_type = (
                record.exc_info[0].__name__
                if record.exc_info is not None and record.exc_info[0] is not None
                else 'FrameworkError'
            )
            event: TelemetryEventInput = {
                'level': 'ERROR' if record.levelno >= logging.ERROR else 'WARNING',
                'event': 'error.unexpected',
                'operation': 'http.request',
                'result': 'failure',
                'error_code': 'internal_error',
                'exception_type': exception_type,
            }
            stack_trace = self._stack_trace(record)
            if stack_trace:
                event['stack_trace'] = stack_trace
            self.provider.emit(event)
        except Exception:  # noqa: BLE001 - logging must never affect the caller.
            return

    @staticmethod
    def _stack_trace(record: logging.LogRecord) -> list[SanitizedStackFrame]:
        if record.exc_info is None or record.exc_info[2] is None:
            return []

        frames = traceback.extract_tb(record.exc_info[2])[-_MAX_STACK_FRAMES:]
        return ConsoleTelemetryProvider.sanitize_stack_trace(
            [
                {
                    'file': frame.filename,
                    'line': frame.lineno,
                    'function': frame.name,
                }
                for frame in frames
            ]
        )


def configure_telemetry_logging(
    provider: TelemetryProvider,
    *,
    log_level: TelemetryLevel,
) -> None:
    """Install one formatter-backed handler for root and Uvicorn loggers."""
    global _telemetry_log_handler

    if _telemetry_log_handler is None:
        _telemetry_log_handler = TelemetryLoggingHandler(provider)
    else:
        _telemetry_log_handler.provider = provider

    handler = _telemetry_log_handler
    handler.setLevel(logging.NOTSET)
    threshold = _LOG_LEVEL_BY_NAME[log_level]
    for logger_name in ('', 'uvicorn', 'uvicorn.error'):
        logger = logging.getLogger(logger_name)
        for existing in tuple(logger.handlers):
            if existing is not handler:
                logger.removeHandler(existing)
        if handler not in logger.handlers:
            logger.addHandler(handler)
        logger.setLevel(threshold)
        logger.propagate = False

    access_logger = logging.getLogger('uvicorn.access')
    for existing in tuple(access_logger.handlers):
        access_logger.removeHandler(existing)
    access_logger.propagate = False

    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
