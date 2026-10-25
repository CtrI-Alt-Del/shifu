import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { TelemetryProvider } from '@/core/shared/interfaces/telemetry-provider'

import { createServerRequestClient } from '../server-request-client'

const mocks = vi.hoisted(() => ({
  axiosRestClient: vi.fn(),
}))

vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: {
    shifuServerAppUrl: 'http://shifu.test',
    bffSharedSecret: 'bff-secret',
  },
}))

vi.mock('../axios-rest-client', () => ({
  AxiosRestClient: mocks.axiosRestClient,
}))

describe('createServerRequestClient', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('marks every API call as coming from the web server', () => {
    createServerRequestClient(undefined)

    expect(mocks.axiosRestClient).toHaveBeenCalledWith('http://shifu.test', {
      defaultHeaders: { 'X-Shifu-Bff-Secret': 'bff-secret' },
      withCredentials: false,
      requestId: undefined,
      telemetry: undefined,
    })
  })

  it('keeps the caller headers, base URL and request telemetry', () => {
    const telemetry = {} as TelemetryProvider

    createServerRequestClient(
      { requestId: 'request-1', telemetry },
      {
        baseUrl: 'http://identity.test',
        defaultHeaders: { 'X-Custom': 'value' },
      },
    )

    expect(mocks.axiosRestClient).toHaveBeenCalledWith('http://identity.test', {
      defaultHeaders: { 'X-Custom': 'value', 'X-Shifu-Bff-Secret': 'bff-secret' },
      withCredentials: false,
      requestId: 'request-1',
      telemetry,
    })
  })

  it('does not let a caller replace the web server mark', () => {
    createServerRequestClient(undefined, {
      defaultHeaders: { 'X-Shifu-Bff-Secret': 'forged' },
    })

    expect(mocks.axiosRestClient).toHaveBeenCalledWith(
      'http://shifu.test',
      expect.objectContaining({
        defaultHeaders: { 'X-Shifu-Bff-Secret': 'bff-secret' },
      }),
    )
  })
})
