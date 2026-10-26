// @vitest-environment node

import { createServer, type IncomingHttpHeaders } from 'node:http'
import type { AddressInfo } from 'node:net'
import axios from 'axios'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { createServerRequestClient } from '@/rest/axios/server-request-client'

const serverEnv = vi.hoisted(() => ({
  shifuServerAppUrl: '',
  bffSharedSecret: 'bff-secret',
}))
vi.mock('@/constants/server-env', () => ({ SERVER_ENV: serverEnv }))

// These internal options cannot be supplied through a browser route. This
// loopback endpoint observes their wire contract with the concrete HTTP client.
describe('Server request origin contract', () => {
  const requests: { path: string; headers: IncomingHttpHeaders }[] = []
  const endpoint = createServer((request, response) => {
    requests.push({ path: request.url ?? '', headers: request.headers })
    response.setHeader('Content-Type', 'application/json')
    response.end(JSON.stringify({ accepted: true }))
  })

  beforeAll(async () => {
    await new Promise<void>((resolve) => endpoint.listen(0, '127.0.0.1', resolve))
    serverEnv.shifuServerAppUrl = `http://127.0.0.1:${(endpoint.address() as AddressInfo).port}`
  })
  afterEach(() => {
    requests.length = 0
    vi.restoreAllMocks()
  })
  afterAll(async () => {
    await new Promise<void>((resolve, reject) =>
      endpoint.close((error) => (error ? reject(error) : resolve())),
    )
  })

  it('marks API requests as server origin and disables implicit credentials', async () => {
    const createClient = vi.spyOn(axios, 'create')
    const response = await createServerRequestClient(undefined).get('/origin', {})

    expect(response.statusCode).toBe(200)
    expect(response.body).toEqual({ accepted: true })
    expect(requests).toEqual([
      expect.objectContaining({
        path: '/origin',
        headers: expect.objectContaining({ 'x-shifu-bff-secret': 'bff-secret' }),
      }),
    ])
    expect(requests[0].headers.cookie).toBeUndefined()
    expect(createClient).toHaveBeenCalledWith(
      expect.objectContaining({ withCredentials: false }),
    )
  })

  it('preserves the explicit origin, caller headers and correlation observation', async () => {
    const telemetry = { emit: vi.fn() }
    const requestId = '123e4567-e89b-42d3-a456-426614174000'
    const client = createServerRequestClient(
      { requestId, telemetry },
      {
        baseUrl: `${serverEnv.shifuServerAppUrl}/identity`,
        defaultHeaders: { 'X-Custom': 'value' },
      },
    )
    const response = await client.get('/session', {
      headers: { Authorization: 'Bearer explicit-access-token' },
    })

    expect(response.statusCode).toBe(200)
    expect(requests[0]).toEqual({
      path: '/identity/session',
      headers: expect.objectContaining({
        'x-custom': 'value',
        'x-shifu-bff-secret': 'bff-secret',
        'x-request-id': requestId,
        authorization: 'Bearer explicit-access-token',
      }),
    })
    expect(telemetry.emit).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'http.request.completed',
        request_id: requestId,
        status_code: 200,
      }),
    )
  })

  it('overwrites a forged internal origin mark before sending the request', async () => {
    await createServerRequestClient(undefined, {
      defaultHeaders: { 'X-Shifu-Bff-Secret': 'forged' },
    }).get('/origin', {})

    expect(requests[0].headers['x-shifu-bff-secret']).toBe('bff-secret')
    expect(JSON.stringify(requests)).not.toContain('forged')
  })
})
