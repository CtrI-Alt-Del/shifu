export const TELEMETRY_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR'] as const
export type TelemetryLevel = (typeof TELEMETRY_LEVELS)[number]

export const TELEMETRY_ENVIRONMENTS = ['dev', 'local', 'staging', 'production'] as const
export type TelemetryEnvironment = (typeof TELEMETRY_ENVIRONMENTS)[number]

export const TELEMETRY_INTEGRATIONS = ['inngest', 'resend', 'openrouter'] as const
export type TelemetryIntegration = (typeof TELEMETRY_INTEGRATIONS)[number]

export const TELEMETRY_RESULTS = ['success', 'failure', 'retry', 'unavailable'] as const
export type TelemetryResult = (typeof TELEMETRY_RESULTS)[number]

export const TELEMETRY_DEPENDENCIES = [
  'database',
  'inngest',
  'resend',
  'openrouter',
  'better-auth',
] as const
export type TelemetryDependency = (typeof TELEMETRY_DEPENDENCIES)[number]

export const TELEMETRY_OPERATIONS = [
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
] as const
export type TelemetryOperation = (typeof TELEMETRY_OPERATIONS)[number]

export const TELEMETRY_JOBS = [
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
  'identity.record_communication_delivery_state',
  'identity.log_main_page_entered',
  'identity.fan_out_unconfirmed_account_expiry',
  'identity.expire_unconfirmed_account',
] as const
export type TelemetryJob = (typeof TELEMETRY_JOBS)[number]

export const TELEMETRY_EVENTS = [
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
] as const
export type TelemetryEventName = (typeof TELEMETRY_EVENTS)[number]

export const TELEMETRY_ERROR_CODES = [
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
] as const
export type TelemetryErrorCode = (typeof TELEMETRY_ERROR_CODES)[number]

export type SanitizedStackFrame = Readonly<{
  file: string
  line?: number
  function?: string
}>

export type TelemetryEventInput = Readonly<{
  level: TelemetryLevel
  event: TelemetryEventName
  request_id?: string
  run_id?: string
  event_id?: string
  method?: string
  route?: string
  status_code?: number
  duration_ms?: number
  operation?: TelemetryOperation
  job?: TelemetryJob
  integration?: TelemetryIntegration
  dependency?: TelemetryDependency
  result?: TelemetryResult
  attempt?: number
  error_code?: TelemetryErrorCode
  exception_type?: string
  stack_trace?: readonly SanitizedStackFrame[]
}>

export type TelemetryEvent = TelemetryEventInput &
  Readonly<{
    timestamp: string
    service: 'shifu-web' | 'shifu-api'
    environment: TelemetryEnvironment
    version: string
    message: string
  }>

export interface TelemetryProvider {
  emit(event: TelemetryEventInput): void
}
