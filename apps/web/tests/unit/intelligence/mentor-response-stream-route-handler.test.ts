import { beforeEach, describe, expect, it, vi } from 'vitest'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { RestResponse } from '@/core/shared/responses/rest-response'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  getStream: vi.fn(),
  fetchRestStreamClient: vi.fn(),
}))

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: unknown) => ({ options }),
}))
vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: { shifuServerAppUrl: 'http://shifu.test' },
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))
vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: vi.fn(() => ({})),
}))
vi.mock('@/rest/fetch/fetch-rest-stream-client', () => ({
  FetchRestStreamClient: (url: string) => {
    mocks.fetchRestStreamClient(url)
    return { getStream: mocks.getStream }
  },
}))

import { Route as eventsRoute } from '@/routes/api/intelligence/mentor-sessions/$sessionId/events'

const SESSION_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0B'

type RouteWithHandlers = {
  options: {
    server?: {
      handlers?: {
        GET?: (context: {
          request: Request
          params: { sessionId: string }
        }) => Promise<Response>
      }
    }
  }
}

function registeredGetHandler() {
  const route = eventsRoute as unknown as RouteWithHandlers
  const handler = route.options.server?.handlers?.GET
  if (!handler) throw new Error('The events route must register a GET handler.')
  return handler
}

describe('Mentor response stream API route handler', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accessToken: 'private-access-token',
      email: 'learner@example.test',
    })
    mocks.getStream.mockResolvedValue(
      new RestResponse({
        body: new ReadableStream<Uint8Array>({
          start(controller) {
            controller.enqueue(new TextEncoder().encode('event: mentor.response\n\n'))
            controller.close()
          },
        }),
        statusCode: 200,
      }),
    )
  })

  it('forwards the cursor through the authenticated REST stream and relays its body', async () => {
    const request = new Request(
      `http://localhost:7000/api/intelligence/mentor-sessions/${SESSION_ID}/events?after_sequence=7`,
    )

    const response = await registeredGetHandler()({
      request,
      params: { sessionId: SESSION_ID },
    })

    expect(mocks.getCurrentAccess).toHaveBeenCalledWith(request)
    expect(mocks.fetchRestStreamClient).toHaveBeenCalledWith('http://shifu.test')
    expect(mocks.getStream).toHaveBeenCalledOnce()
    const [path, options] = mocks.getStream.mock.calls[0] ?? []
    expect(path).toBe(`/intelligence/mentor-sessions/${SESSION_ID}/events`)
    expect(options).toMatchObject({
      headers: {
        Authorization: 'Bearer private-access-token',
        'Cache-Control': 'no-store',
        Accept: 'text/event-stream',
        'Last-Event-ID': '7',
      },
    })
    expect(options.signal).toBeInstanceOf(AbortSignal)
    expect(response.status).toBe(200)
    expect(response.headers.get('cache-control')).toBe('no-store')
    expect(response.headers.get('content-type')).toBe('text/event-stream')
    expect(await response.text()).toBe('event: mentor.response\n\n')
  })

  it('returns the upstream failure status without exposing its message', async () => {
    mocks.getStream.mockResolvedValueOnce(
      new RestResponse({
        statusCode: 503,
        errorMessage: 'Private upstream details',
      }),
    )
    const request = new Request(
      `http://localhost:7000/api/intelligence/mentor-sessions/${SESSION_ID}/events`,
    )

    const response = await registeredGetHandler()({
      request,
      params: { sessionId: SESSION_ID },
    })

    expect(response.status).toBe(HTTP_STATUS_CODE.serviceUnavailable)
    expect(response.headers.get('cache-control')).toBe('no-store')
    expect(response.headers.get('content-type')).toBe('text/event-stream')
    expect(await response.text()).toBe('')
  })
})
