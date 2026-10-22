import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'

import { FetchRestStreamClient } from '../fetch-rest-stream-client'

describe('FetchRestStreamClient', () => {
  const requestId = '11111111-1111-4111-8111-111111111111'

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response('event: mentor.response\n\n', {
          headers: { 'X-Request-ID': '22222222-2222-4222-8222-222222222222' },
        }),
      ),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('forwards server request context and records the API response correlation', async () => {
    const telemetry = { emit: vi.fn() }
    const context = { requestId, telemetry } satisfies RequestTelemetryContext
    const response = await FetchRestStreamClient('https://api.test', context).getStream(
      '/events',
      { headers: { Accept: 'text/event-stream' }, signal: new AbortController().signal },
    )

    expect(fetch).toHaveBeenCalledWith(
      'https://api.test/events',
      expect.objectContaining({
        headers: {
          Accept: 'text/event-stream',
          'X-Request-ID': requestId,
        },
      }),
    )
    expect(response.statusCode).toBe(200)
    expect(telemetry.emit).toHaveBeenCalledWith({
      level: 'INFO',
      event: 'http.request.completed',
      request_id: '22222222-2222-4222-8222-222222222222',
      method: 'GET',
      route: 'unmatched',
      status_code: 200,
      operation: 'http.request',
      result: 'success',
    })
  })

  it('keeps browser stream calls context-free', async () => {
    const response = await FetchRestStreamClient('https://api.test').getStream(
      '/events',
      {
        headers: { Accept: 'text/event-stream' },
        signal: new AbortController().signal,
      },
    )

    expect(response.statusCode).toBe(200)
    expect(fetch).toHaveBeenCalledWith(
      'https://api.test/events',
      expect.objectContaining({
        headers: { Accept: 'text/event-stream' },
      }),
    )
  })
})
