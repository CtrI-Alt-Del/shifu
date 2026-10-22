import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'

const axiosRestClient = vi.hoisted(() => vi.fn())
vi.mock('@/rest/axios/axios-rest-client', () => ({ AxiosRestClient: axiosRestClient }))

import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { observeResponseCorrelation } from '@/rest/telemetry/observe-response-correlation'

describe('Web telemetry transport boundaries', () => {
  beforeEach(() => vi.clearAllMocks())

  it('builds a server REST client with the full request telemetry context', () => {
    const context = {
      requestId: '11111111-1111-4111-8111-111111111111',
      telemetry: { emit: vi.fn() },
    } satisfies RequestTelemetryContext
    const client = { get: vi.fn() }
    axiosRestClient.mockReturnValue(client)

    expect(
      createServerRequestClient(context, {
        baseUrl: 'http://identity.test',
        defaultHeaders: { 'X-Shifu-Bff-Secret': 'shared-secret' },
      }),
    ).toBe(client)
    expect(axiosRestClient).toHaveBeenCalledWith('http://identity.test', {
      defaultHeaders: { 'X-Shifu-Bff-Secret': 'shared-secret' },
      withCredentials: false,
      requestId: context.requestId,
      telemetry: context.telemetry,
    })
  })

  it('prefers a valid response correlation ID and falls back to the request ID', () => {
    const telemetry = { emit: vi.fn() }
    const requestId = '11111111-1111-4111-8111-111111111111'
    const responseId = '22222222-2222-4222-8222-222222222222'

    observeResponseCorrelation(telemetry, {
      method: 'GET',
      requestId,
      responseRequestId: responseId,
      statusCode: 200,
    })
    observeResponseCorrelation(telemetry, {
      method: 'POST',
      requestId,
      responseRequestId: 'not-a-uuid',
      statusCode: 503,
    })

    expect(telemetry.emit).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ request_id: responseId, result: 'success' }),
    )
    expect(telemetry.emit).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        request_id: requestId,
        level: 'ERROR',
        result: 'failure',
      }),
    )
  })

  it('swallows telemetry provider failures without changing the request result', () => {
    const telemetry = {
      emit: vi.fn(() => {
        throw new Error('telemetry failed')
      }),
    }

    expect(() =>
      observeResponseCorrelation(telemetry, {
        method: 'GET',
        statusCode: 0,
      }),
    ).not.toThrow()
  })
})
