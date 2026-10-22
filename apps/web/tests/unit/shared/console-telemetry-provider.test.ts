import { afterEach, describe, expect, it, vi } from 'vitest'

import { ConsoleTelemetryProvider } from '@/provision/telemetry/console-telemetry-provider'

describe('ConsoleTelemetryProvider', () => {
  afterEach(() => vi.restoreAllMocks())

  it('serializes allowlisted fields and safe stack basenames without raw paths', () => {
    const log = vi.spyOn(console, 'log').mockImplementation(() => undefined)
    const provider = new ConsoleTelemetryProvider({
      environment: 'local',
      logLevel: 'DEBUG',
      version: 'test-version',
    })

    provider.emit({
      level: 'ERROR',
      event: 'error.unexpected',
      request_id: '11111111-1111-4111-8111-111111111111',
      method: 'POST',
      route: '/api/auth/$',
      operation: 'http.request',
      error_code: 'internal_error',
      exception_type: 'Error',
      stack_trace: [
        { file: 'C:\\private\\auth.ts', line: 17, function: 'handleAuthRequest' },
        { file: 'C:\\private\\bad secret.ts', line: 18 },
      ],
    })

    const payload = JSON.parse(log.mock.calls[0]?.[0] as string) as Record<
      string,
      unknown
    >
    expect(payload).toMatchObject({
      service: 'shifu-web',
      environment: 'local',
      version: 'test-version',
      event: 'error.unexpected',
      error_code: 'internal_error',
    })
    expect(payload.stack_trace).toEqual([
      { file: 'auth.ts', line: 17, function: 'handleAuthRequest' },
    ])
    expect(JSON.stringify(payload)).not.toContain('C:\\private')
    expect(JSON.stringify(payload)).not.toContain('bad secret')
  })

  it('filters below-threshold events and reports the version only once', () => {
    const log = vi.spyOn(console, 'log').mockImplementation(() => undefined)
    const provider = new ConsoleTelemetryProvider({
      environment: 'local',
      logLevel: 'INFO',
      version: 'test-version',
    })

    provider.emit({ level: 'DEBUG', event: 'app.version.reported' })
    provider.reportVersionOnce()
    provider.reportVersionOnce()

    expect(log).toHaveBeenCalledOnce()
    expect(JSON.parse(log.mock.calls[0]?.[0] as string).event).toBe(
      'app.version.reported',
    )
  })

  it('ignores malformed events and keeps emission best effort', () => {
    const log = vi.spyOn(console, 'log').mockImplementation(() => undefined)
    const provider = new ConsoleTelemetryProvider({
      environment: 'local',
      logLevel: 'DEBUG',
      version: 'test-version',
    })

    provider.emit({ level: 'INVALID', event: 'app.version.reported' } as never)
    provider.emit({ level: 'INFO', event: 'invalid.event' } as never)

    log.mockImplementationOnce(() => {
      throw new Error('console unavailable')
    })
    provider.emit({ level: 'INFO', event: 'app.version.reported' })

    expect(log).toHaveBeenCalledTimes(1)
  })

  it('accepts the complete allowlisted field set and drops invalid values', () => {
    const log = vi.spyOn(console, 'log').mockImplementation(() => undefined)
    const provider = new ConsoleTelemetryProvider({
      environment: 'local',
      logLevel: 'DEBUG',
      version: 'test-version',
    })

    provider.emit({
      level: 'INFO',
      event: 'http.request.completed',
      request_id: '11111111-1111-4111-8111-111111111111',
      run_id: 'run-1',
      event_id: 'event-1',
      method: 'GET',
      route: 'unmatched',
      status_code: 200,
      duration_ms: 1.5,
      operation: 'http.request',
      integration: 'openrouter',
      dependency: 'better-auth',
      result: 'success',
      attempt: 1,
      error_code: 'internal_error',
      exception_type: 'Error',
      stack_trace: [{ file: 'server.ts', line: 1, function: 'handler' }],
    })
    provider.emit({
      level: 'INFO',
      event: 'http.request.completed',
      request_id: 'not-a-uuid',
      run_id: 'bad value',
      event_id: 'bad value',
      method: 'get',
      route: 'not-a-route',
      status_code: 99,
      duration_ms: -1,
      operation: 'not-allowed',
      result: 'not-allowed',
      attempt: 0,
      exception_type: 'bad value',
      stack_trace: [{ file: 'bad file.ts' }],
    } as never)

    expect(log).toHaveBeenCalledTimes(2)
  })
})
