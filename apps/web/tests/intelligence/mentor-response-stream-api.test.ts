import { buildMentorResponseEventsPath } from '../../src/constants/routes'
import { expect, signInPassword, test } from '../playwright'

// Registered HTTP handler with real Better Auth cookies. The controlled-open
// upstream streaming matrix additionally needs the task-owned upstream fixture.
const SESSION_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
test.describe('Mentor response SSE HTTP handler', () => {
  test('rejects anonymous access without forwarding private transport headers', async ({
    request,
  }) => {
    const response = await request.get(buildMentorResponseEventsPath(SESSION_ID))
    expect(response.status()).toBe(401)
    expect(response.headers()['cache-control']).toBe('no-store')
    expect(response.headers()['set-cookie']).toBeUndefined()
    expect(response.headers().authorization).toBeUndefined()
    expect(await response.text()).toBe('')
  })
  test('rejects an invalid session cookie before opening a private upstream stream', async ({
    request,
  }) => {
    const response = await request.get(buildMentorResponseEventsPath(SESSION_ID), {
      headers: { Cookie: 'better-auth.session_token=expired.invalid' },
    })
    expect(response.status()).toBe(401)
    expect(response.headers()['cache-control']).toBe('no-store')
    expect(await response.text()).toBe('')
  })
  for (const cursor of ['-1', 'abc', '1.2', '9007199254740992']) {
    test(`rejects malformed replay cursor ${cursor}`, async ({ request }) => {
      const response = await request.get(
        `${buildMentorResponseEventsPath(SESSION_ID)}?after_sequence=${encodeURIComponent(cursor)}`,
      )
      expect(response.status()).toBe(422)
      expect(response.headers()['cache-control']).toBe('no-store')
      expect(await response.text()).toBe('')
    })
  }
  test('validates Last-Event-ID before the initial query cursor', async ({ request }) => {
    const response = await request.get(
      `${buildMentorResponseEventsPath(SESSION_ID)}?after_sequence=0`,
      { headers: { 'Last-Event-ID': '-1' } },
    )
    expect(response.status()).toBe(422)
  })
})

type BrowserStreamState = {
  content: string
  done: boolean
  status: number | null
  headers: Record<string, string>
  controller: AbortController
  error: string | null
}
declare global {
  interface Window {
    mentorHandlerStream?: BrowserStreamState
  }
}

// This matrix uses real Identity/Better Auth and the registered BFF handler.
// Only Intelligence's upstream body is controlled by a test-owned reverse proxy.
// Run with SHIFU_MENTOR_STREAM_TEST_PROXY_PORT and isolated auth/server databases.
test.describe('Mentor response authenticated incremental HTTP stream', () => {
  test.beforeEach(async ({ page, activeAccount }) => {
    const signIn = await page.request.post('/api/auth/sign-in/identity', {
      data: { email: activeAccount.email, password: signInPassword },
      headers: { 'x-forwarded-for': activeAccount.ipAddress },
    })
    expect(signIn.status()).toBe(200)
    // A same-origin JSON document gives browser fetch the real cookie context
    // without mounting or mocking a product Page or triggering another journey.
    await page.goto('/api/auth/get-session')
  })
  test('delivers fragmented UTF-8 multiline SSE before upstream completion with safe headers and owner authentication', async ({
    page,
    activeAccount,
    mentorStream,
  }) => {
    const event = {
      session_id: mentorStream.sessionId,
      attempt_id: '01MT0000000000000000000001',
      sequence: 4,
      kind: 'block',
      status: 'processing',
      block: {
        block_key: 'unicode',
        ordinal: 0,
        intent: null,
        content: 'Orientação aprovada: café, ação e 🧠.',
      },
      consultation: null,
      failure_code: null,
      created_at: '2026-10-10T00:00:00Z',
    }
    const initialChunk = `id:4\nevent:mentor.response\n${JSON.stringify(event, null, 2)
      .split('\n')
      .map((line) => `data:${line}`)
      .join('\n')}\n\n`
    const finalChunk = `id:5\nevent:mentor.response\ndata:${JSON.stringify({ ...event, sequence: 5, kind: 'completed', status: 'completed', block: null })}\n\n`
    await mentorStream.register({ initialChunk, finalChunk })
    await startBrowserStream(page, `${mentorStream.path}?after_sequence=3`)
    await expect
      .poll(() => page.evaluate(() => window.mentorHandlerStream?.content))
      .toBe(initialChunk)
    const state = await page.evaluate(() => ({
      done: window.mentorHandlerStream?.done,
      status: window.mentorHandlerStream?.status,
      headers: window.mentorHandlerStream?.headers,
    }))
    expect(state.done).toBe(false)
    expect(state.status).toBe(200)
    expect(state.headers?.['content-type']).toContain('text/event-stream')
    expect(state.headers?.['cache-control']).toBe('no-store')
    expect(state.headers?.authorization).toBeUndefined()
    expect(state.headers?.['set-cookie']).toBeUndefined()
    expect(state.headers?.['x-provider-secret']).toBeUndefined()
    expect(await mentorStream.observations()).toEqual(
      expect.objectContaining({
        calls: 1,
        ended: false,
        closed: false,
        upstreamAuthorization: true,
        upstreamCookie: false,
        authorizedAccount: activeAccount.accountId,
        cursor: '3',
      }),
    )
    await mentorStream.release()
    await expect
      .poll(() => page.evaluate(() => window.mentorHandlerStream?.done))
      .toBe(true)
    expect(await page.evaluate(() => window.mentorHandlerStream?.content)).toBe(
      initialChunk + finalChunk,
    )
  })
  test('uses Last-Event-ID instead of the initial cursor and aborts upstream without a cancel operation', async ({
    page,
    mentorStream,
  }) => {
    await mentorStream.register({ initialChunk: ':heartbeat\n\n' })
    await startBrowserStream(page, `${mentorStream.path}?after_sequence=malformed`, {
      'Last-Event-ID': '9',
    })
    await expect
      .poll(() => page.evaluate(() => window.mentorHandlerStream?.content))
      .toBe(':heartbeat\n\n')
    expect((await mentorStream.observations()).cursor).toBe('9')
    await page.evaluate(() => window.mentorHandlerStream?.controller.abort())
    await expect.poll(async () => (await mentorStream.observations()).closed).toBe(true)
    expect((await mentorStream.observations()).calls).toBe(1)
    expect((await mentorStream.observations()).ended).toBe(false)
    expect((await mentorStream.observations()).cancelCalls).toBe(0)
  })
  for (const status of [401, 403, 503]) {
    test(`sanitizes upstream ${status} and keeps no-store without private headers`, async ({
      page,
      mentorStream,
    }) => {
      await mentorStream.register({ status })
      const response = await page.request.get(mentorStream.path)
      expect(response.status()).toBe(status)
      expect(response.headers()['cache-control']).toBe('no-store')
      expect(response.headers().authorization).toBeUndefined()
      expect(response.headers()['set-cookie']).toBeUndefined()
      expect(response.headers()['x-provider-secret']).toBeUndefined()
      expect(await response.text()).toBe('')
      expect((await mentorStream.observations()).calls).toBe(1)
    })
  }
  test('keeps a foreign resource private while forwarding only the authenticated owner identity', async ({
    page,
    activeAccount,
    mentorStream,
  }) => {
    await mentorStream.register({ ownerAccountId: '01MT0000000000000000000009' })
    const response = await page.request.get(mentorStream.path)
    expect(response.status()).toBe(404)
    expect(await response.text()).toBe('')
    expect((await mentorStream.observations()).authorizedAccount).toBe(
      activeAccount.accountId,
    )
  })
  for (const mode of ['expire', 'revoke'] as const) {
    test(`rejects ${mode}d real account access before Intelligence upstream is called`, async ({
      page,
      mentorStream,
    }) => {
      await mentorStream.register()
      await mentorStream.changeAccountAccess(mode)
      const response = await page.request.get(mentorStream.path)
      expect(response.status()).toBe(401)
      expect(response.headers()['cache-control']).toBe('no-store')
      expect(await response.text()).toBe('')
      expect((await mentorStream.observations()).calls).toBe(0)
    })
  }
})

async function startBrowserStream(
  page: import('@playwright/test').Page,
  path: string,
  headers: Record<string, string> = {},
) {
  await page.evaluate(
    ({ path, headers }) => {
      const state: BrowserStreamState = {
        content: '',
        done: false,
        status: null,
        headers: {},
        controller: new AbortController(),
        error: null,
      }
      window.mentorHandlerStream = state
      void (async () => {
        try {
          const response = await fetch(path, { headers, signal: state.controller.signal })
          state.status = response.status
          state.headers = Object.fromEntries(response.headers.entries())
          if (!response.body) throw new Error('The response body is missing')
          const reader = response.body.getReader()
          const decoder = new TextDecoder()
          while (true) {
            const chunk = await reader.read()
            if (chunk.done) break
            state.content += decoder.decode(chunk.value, { stream: true })
          }
          state.content += decoder.decode()
        } catch (error) {
          state.error = error instanceof Error ? error.name : 'unknown'
        } finally {
          state.done = true
        }
      })()
    },
    { path, headers },
  )
}
