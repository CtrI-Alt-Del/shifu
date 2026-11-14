import {
  TELEMETRY_DEPENDENCIES,
  TELEMETRY_ERROR_CODES,
  TELEMETRY_EVENTS,
  TELEMETRY_INTEGRATIONS,
  TELEMETRY_JOBS,
  TELEMETRY_LEVELS,
  TELEMETRY_OPERATIONS,
  TELEMETRY_RESULTS,
  type SanitizedStackFrame,
  type TelemetryEnvironment,
  type TelemetryEventInput,
  type TelemetryEventName,
  type TelemetryLevel,
  type TelemetryProvider,
} from '@/core/shared/interfaces/telemetry-provider'
import { SERVER_ENV } from '@/constants/server-env'

const LEVEL_RANK: Record<TelemetryLevel, number> = {
  DEBUG: 10,
  INFO: 20,
  WARNING: 30,
  ERROR: 40,
}

const MESSAGE_BY_EVENT: Record<TelemetryEventName, string> = {
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

const UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const OPAQUE_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/
const SAFE_TEXT_PATTERN = /^[A-Za-z0-9_.:-]{1,120}$/
const ROUTE_PATTERN = /^(?:\/[A-Za-z0-9_$.:{}-]+)+\/?$/

export type ConsoleTelemetryProviderOptions = Readonly<{
  environment: TelemetryEnvironment
  logLevel: TelemetryLevel
  version: string
  service?: 'shifu-web'
}>

export class ConsoleTelemetryProvider implements TelemetryProvider {
  private readonly options: ConsoleTelemetryProviderOptions
  private versionReported = false

  constructor(options: ConsoleTelemetryProviderOptions) {
    this.options = options
  }

  emit(event: TelemetryEventInput): void {
    try {
      if (!isTelemetryLevel(event.level) || !isTelemetryEventName(event.event)) return
      if (LEVEL_RANK[event.level] < LEVEL_RANK[this.options.logLevel]) return

      const payload = this.sanitize(event)
      if (payload === null) return
      console.log(JSON.stringify(payload))
    } catch {
      // Telemetry is best effort and must never change the business outcome.
    }
  }

  reportVersionOnce(requestId?: string): void {
    if (this.versionReported) return
    this.versionReported = true
    this.emit({
      level: 'INFO',
      event: 'app.version.reported',
      request_id: requestId,
      operation: 'app.startup',
      result: 'success',
    })
  }

  private sanitize(event: TelemetryEventInput): Record<string, unknown> | null {
    const payload: Record<string, unknown> = {
      timestamp: new Date().toISOString(),
      level: event.level,
      service: this.options.service ?? 'shifu-web',
      environment: this.options.environment,
      version: this.options.version,
      event: event.event,
      message: MESSAGE_BY_EVENT[event.event],
    }

    addIfDefined(payload, 'request_id', sanitizeUuid(event.request_id))
    addIfDefined(payload, 'run_id', sanitizeOpaqueId(event.run_id))
    addIfDefined(payload, 'event_id', sanitizeOpaqueId(event.event_id))
    addIfDefined(payload, 'method', sanitizeMethod(event.method))
    addIfDefined(payload, 'route', sanitizeRoute(event.route))
    addIfDefined(payload, 'status_code', sanitizeStatusCode(event.status_code))
    addIfDefined(payload, 'duration_ms', sanitizeDuration(event.duration_ms))
    addIfDefined(
      payload,
      'operation',
      sanitizeCatalog(event.operation, TELEMETRY_OPERATIONS),
    )
    addIfDefined(payload, 'job', sanitizeCatalog(event.job, TELEMETRY_JOBS))
    addIfDefined(
      payload,
      'integration',
      sanitizeCatalog(event.integration, TELEMETRY_INTEGRATIONS),
    )
    addIfDefined(
      payload,
      'dependency',
      sanitizeCatalog(event.dependency, TELEMETRY_DEPENDENCIES),
    )
    addIfDefined(payload, 'result', sanitizeCatalog(event.result, TELEMETRY_RESULTS))
    addIfDefined(payload, 'attempt', sanitizeAttempt(event.attempt))
    addIfDefined(
      payload,
      'error_code',
      sanitizeCatalog(event.error_code, TELEMETRY_ERROR_CODES),
    )
    addIfDefined(payload, 'exception_type', sanitizeSafeText(event.exception_type))
    addIfDefined(payload, 'stack_trace', sanitizeStackTrace(event.stack_trace))

    return payload
  }
}

export function createConsoleTelemetryProvider(): ConsoleTelemetryProvider {
  return new ConsoleTelemetryProvider({
    environment: SERVER_ENV.telemetryEnvironment,
    logLevel: SERVER_ENV.telemetryLogLevel,
    version: SERVER_ENV.releaseVersion,
  })
}

let webTelemetryProvider: ConsoleTelemetryProvider | undefined

export function getWebTelemetryProvider(): ConsoleTelemetryProvider {
  webTelemetryProvider ??= createConsoleTelemetryProvider()
  return webTelemetryProvider
}

function addIfDefined(
  payload: Record<string, unknown>,
  key: string,
  value: unknown,
): void {
  if (value !== undefined) payload[key] = value
}

function isTelemetryLevel(value: unknown): value is TelemetryLevel {
  return typeof value === 'string' && TELEMETRY_LEVELS.includes(value as TelemetryLevel)
}

function isTelemetryEventName(value: unknown): value is TelemetryEventName {
  return (
    typeof value === 'string' && TELEMETRY_EVENTS.includes(value as TelemetryEventName)
  )
}

function sanitizeUuid(value: unknown): string | undefined {
  return typeof value === 'string' && UUID_V4_PATTERN.test(value) ? value : undefined
}

function sanitizeOpaqueId(value: unknown): string | undefined {
  return typeof value === 'string' && OPAQUE_ID_PATTERN.test(value) ? value : undefined
}

function sanitizeMethod(value: unknown): string | undefined {
  return typeof value === 'string' && /^[A-Z]{3,10}$/.test(value) ? value : undefined
}

function sanitizeRoute(value: unknown): string | undefined {
  return value === 'unmatched' || (typeof value === 'string' && ROUTE_PATTERN.test(value))
    ? value
    : undefined
}

function sanitizeStatusCode(value: unknown): number | undefined {
  return typeof value === 'number' &&
    Number.isInteger(value) &&
    value >= 100 &&
    value <= 599
    ? value
    : undefined
}

function sanitizeDuration(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
    ? value
    : undefined
}

function sanitizeAttempt(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isInteger(value) && value >= 1
    ? value
    : undefined
}

function sanitizeSafeText(value: unknown): string | undefined {
  return typeof value === 'string' && SAFE_TEXT_PATTERN.test(value) ? value : undefined
}

function sanitizeCatalog<const Values extends readonly string[]>(
  value: unknown,
  allowed: Values,
): Values[number] | undefined {
  return typeof value === 'string' && allowed.includes(value) ? value : undefined
}

function sanitizeStackTrace(value: unknown): readonly SanitizedStackFrame[] | undefined {
  if (!Array.isArray(value)) return undefined

  const frames = value.slice(0, 20).flatMap((frame): SanitizedStackFrame[] => {
    if (!isRecord(frame) || typeof frame.file !== 'string') return []
    const file = frame.file.split(/[\\/]/).pop()
    if (!file || !SAFE_TEXT_PATTERN.test(file)) return []

    const sanitized: SanitizedStackFrame = {
      file,
      ...(typeof frame.line === 'number' && Number.isInteger(frame.line) && frame.line > 0
        ? { line: frame.line }
        : {}),
      ...(typeof frame.function === 'string' && SAFE_TEXT_PATTERN.test(frame.function)
        ? { function: frame.function }
        : {}),
    }
    return [sanitized]
  })

  return frames.length > 0 ? frames : undefined
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
