from typing import Literal, NotRequired, Protocol, Required, TypedDict

TelemetryLevel = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']
TelemetryEnvironment = Literal['dev', 'local', 'staging', 'production']
TelemetryService = Literal['shifu-web', 'shifu-api']
TelemetryIntegration = Literal['inngest', 'resend', 'openrouter']
TelemetryResult = Literal['success', 'failure', 'retry', 'unavailable']
TelemetryDependency = Literal[
    'database', 'inngest', 'resend', 'openrouter', 'better-auth'
]
TelemetryOperation = Literal[
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
]
TelemetryEventName = Literal[
    'http.request.completed',
    'http.request.failed',
    'error.unexpected',
    'auth.login.succeeded',
    'auth.login.refused',
    'auth.session.revoked',
    'auth.access.denied',
    'learning.goal.created',
    'learning.goal.deleted',
    'learning.attempt.submitted',
    'learning.evaluation.completed',
    'job.started',
    'job.completed',
    'job.failed',
    'job.retrying',
    'integration.operation.started',
    'integration.operation.completed',
    'integration.operation.failed',
    'integration.operation.retrying',
    'app.startup.completed',
    'app.shutdown.completed',
    'app.version.reported',
    'dependency.unavailable',
]
TelemetryErrorCode = Literal[
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
]
TelemetryJob = Literal[
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
]


class SanitizedStackFrame(TypedDict, total=False):
    file: Required[str]
    line: NotRequired[int]
    function: NotRequired[str]


class TelemetryEventInput(TypedDict, total=False):
    level: Required[TelemetryLevel]
    event: Required[TelemetryEventName]
    request_id: NotRequired[str]
    run_id: NotRequired[str]
    event_id: NotRequired[str]
    method: NotRequired[str]
    route: NotRequired[str]
    status_code: NotRequired[int]
    duration_ms: NotRequired[float]
    operation: NotRequired[TelemetryOperation]
    job: NotRequired[TelemetryJob]
    integration: NotRequired[TelemetryIntegration]
    dependency: NotRequired[TelemetryDependency]
    result: NotRequired[TelemetryResult]
    attempt: NotRequired[int]
    error_code: NotRequired[TelemetryErrorCode]
    exception_type: NotRequired[str]
    stack_trace: NotRequired[list[SanitizedStackFrame]]


class TelemetryEvent(TelemetryEventInput, total=False):
    timestamp: Required[str]
    service: Required[TelemetryService]
    environment: Required[TelemetryEnvironment]
    version: Required[str]
    message: Required[str]


class TelemetryProvider(Protocol):
    """Framework-independent sink for allowlisted technical telemetry."""

    def emit(self, event: TelemetryEventInput) -> None:
        """Best-effort emission of one typed telemetry input event."""
        ...
