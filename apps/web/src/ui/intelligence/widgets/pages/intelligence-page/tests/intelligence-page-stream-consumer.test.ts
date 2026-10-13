import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Route } from '@/routes/api/intelligence/mentor-sessions/$sessionId/events'
const ports = vi.hoisted(() => ({ access: vi.fn(), fetch: vi.fn() }))
vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: unknown) => options,
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: ports.access }),
}))
const sessionId = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
const handler = (
  Route as unknown as {
    server: {
      handlers: {
        GET(input: { request: Request; params: { sessionId: string } }): Promise<Response>
      }
    }
  }
).server.handlers.GET
const request = (suffix = '', signal?: AbortSignal, headers?: HeadersInit) =>
  new Request(
    `http://localhost/api/intelligence/mentor-sessions/${sessionId}/events${suffix}`,
    { signal, headers },
  )
describe('Intelligence page HTTP stream boundary consumer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ports.access.mockResolvedValue({
      email: 'learner@example.com',
      accessToken: 'test-token',
    })
    vi.stubGlobal('fetch', ports.fetch)
  })
  afterEach(() => vi.unstubAllGlobals())
  it('forwards approved chunks incrementally with authoritative resume headers and no private upstream headers', async () => {
    let upstream!: ReadableStreamDefaultController<Uint8Array>
    ports.fetch.mockResolvedValue(
      new Response(
        new ReadableStream({
          start(controller) {
            upstream = controller
          },
        }),
        { headers: { 'X-Provider-Secret': 'private' } },
      ),
    )
    const response = await handler({
      request: request('?after_sequence=invalid', undefined, { 'Last-Event-ID': '9' }),
      params: { sessionId },
    })
    expect(response.status).toBe(200)
    expect(response.headers.get('Cache-Control')).toBe('no-store')
    expect(response.headers.get('Content-Type')).toBe('text/event-stream')
    expect(response.headers.get('X-Provider-Secret')).toBeNull()
    const options = ports.fetch.mock.calls[0]?.[1]
    expect(options).toEqual(
      expect.objectContaining({
        cache: 'no-store',
        redirect: 'error',
        headers: {
          Authorization: 'Bearer test-token',
          'Cache-Control': 'no-store',
          Accept: 'text/event-stream',
          'Last-Event-ID': '9',
        },
      }),
    )
    const reader = requiredBody(response).getReader()
    upstream.enqueue(new TextEncoder().encode('data: olá\n\n'))
    expect(new TextDecoder().decode((await reader.read()).value)).toBe('data: olá\n\n')
    upstream.close()
    expect((await reader.read()).done).toBe(true)
  })
  it('aborts only the upstream transport when the page reader disconnects', async () => {
    const cancel = vi.fn()
    ports.fetch.mockResolvedValue(new Response(new ReadableStream({ cancel })))
    const response = await handler({ request: request(), params: { sessionId } })
    await requiredBody(response).cancel()
    expect(cancel).toHaveBeenCalledOnce()
    expect(ports.fetch.mock.calls[0]?.[1].signal.aborted).toBe(true)
  })
  it('propagates request cancellation, including an already aborted request', async () => {
    const controller = new AbortController()
    controller.abort()
    ports.fetch.mockRejectedValue(new Error('private network diagnostic'))
    const response = await handler({
      request: request('', controller.signal),
      params: { sessionId },
    })
    expect(response.status).toBe(503)
    expect(ports.fetch.mock.calls[0]?.[1].signal.aborted).toBe(true)
    expect(await response.text()).toBe('')
  })
  it('fences a broken upstream read and returns only a generic stream error', async () => {
    let upstream!: ReadableStreamDefaultController<Uint8Array>
    ports.fetch.mockResolvedValue(
      new Response(
        new ReadableStream({
          start(controller) {
            upstream = controller
          },
        }),
      ),
    )
    const response = await handler({ request: request(), params: { sessionId } })
    const read = requiredBody(response).getReader().read()
    upstream.error(new Error('private provider diagnostic'))
    await expect(read).rejects.toThrow('A conexão da resposta foi interrompida.')
    expect(ports.fetch.mock.calls[0]?.[1].signal.aborted).toBe(true)
  })
  it.each([401, 403, 503])('keeps upstream %s safe and uncached', async (status) => {
    ports.fetch.mockResolvedValue(new Response('private provider diagnostic', { status }))
    const response = await handler({ request: request(), params: { sessionId } })
    expect(response.status).toBe(status)
    expect(await response.text()).toBe('')
    expect(response.headers.get('Cache-Control')).toBe('no-store')
  })
  it('rejects an anonymous page before contacting Intelligence', async () => {
    ports.access.mockResolvedValue(null)
    const response = await handler({ request: request(), params: { sessionId } })
    expect(response.status).toBe(401)
    expect(ports.fetch).not.toHaveBeenCalled()
  })
  it.each([
    ['?after_sequence=-1', sessionId],
    ['?after_sequence=9007199254740992', sessionId],
    ['', 'bad-id'],
  ])('rejects malformed routing %s %s before authorization', async (suffix, id) => {
    const response = await handler({
      request: request(suffix),
      params: { sessionId: id },
    })
    expect(response.status).toBe(422)
    expect(ports.access).not.toHaveBeenCalled()
  })
  it('handles a successful upstream without a body as a safe unavailable response', async () => {
    ports.fetch.mockResolvedValue(new Response(null))
    const response = await handler({ request: request(), params: { sessionId } })
    expect(response.status).toBe(503)
    expect(await response.text()).toBe('')
  })
})

function requiredBody(response: Response) {
  if (!response.body) throw new Error('Expected streaming response body')
  return response.body
}
