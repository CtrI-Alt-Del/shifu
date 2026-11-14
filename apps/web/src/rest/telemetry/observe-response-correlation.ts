import type { TelemetryProvider } from '@/core/shared/interfaces/telemetry-provider'

const UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export type ResponseCorrelationObservation = Readonly<{
  method: string
  requestId?: string
  responseRequestId?: string
  statusCode: number
}>

export function observeResponseCorrelation(
  telemetry: TelemetryProvider | undefined,
  observation: ResponseCorrelationObservation,
): void {
  if (!telemetry) return

  const requestId = isUuidV4(observation.responseRequestId)
    ? observation.responseRequestId
    : isUuidV4(observation.requestId)
      ? observation.requestId
      : undefined
  const isFailure = observation.statusCode < 200 || observation.statusCode >= 300

  try {
    telemetry.emit({
      level: isFailure
        ? observation.statusCode >= 500 || observation.statusCode === 0
          ? 'ERROR'
          : 'WARNING'
        : 'INFO',
      event: isFailure ? 'http.request.failed' : 'http.request.completed',
      ...(requestId ? { request_id: requestId } : {}),
      method: observation.method,
      route: 'unmatched',
      ...(observation.statusCode > 0 ? { status_code: observation.statusCode } : {}),
      operation: 'http.request',
      result: isFailure ? 'failure' : 'success',
    })
  } catch {
    // Response observation is best effort and must not change the REST result.
  }
}

export function isUuidV4(value: string | undefined): value is string {
  return value !== undefined && UUID_V4_PATTERN.test(value)
}
