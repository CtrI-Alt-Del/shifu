// @vitest-environment node

import { createHash } from 'node:crypto'
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import { Pool } from 'pg'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'

import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import type { IdentityProfile } from '@/rest/services/identity-service'

const trackedPools = vi.hoisted(() => [] as Array<{ end: () => Promise<void> }>)

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: unknown) => ({ options }),
}))

vi.mock('pg', async (importOriginal) => {
  const actual = await importOriginal<typeof import('pg')>()

  class TrackedPool extends actual.Pool {
    constructor(...args: ConstructorParameters<typeof actual.Pool>) {
      super(...args)
      trackedPools.push(this)
    }
  }

  return { ...actual, Pool: TrackedPool }
})

import { Route as authRoute } from '@/routes/api/auth/$'
import { Route as accountDeletionRoute } from '@/routes/api/auth/account/deletion/'
import { Route as accountDeletionPrepareRoute } from '@/routes/api/auth/account/deletion/prepare'
import { Route as accountClosureRoute } from '@/routes/api/internal/identity/account-closure'
import { Route as browserCapabilityRoute } from '@/routes/api/identity/browser-data-capabilities/'
import { Route as browserCapabilityValidationRoute } from '@/routes/api/identity/browser-data-validations/'

const BASE_URL = 'http://127.0.0.1:7000'
const ACCOUNT_ID = '01J00000000000000000000098'
const CLOSED_AT = '2026-11-21T12:00:00Z'
const TEST_CLIENT_IPS = [
  '198.51.100.10',
  '198.51.100.11',
  '198.51.100.12',
  '198.51.100.13',
  '198.51.100.14',
  '198.51.100.18',
] as const
const TELEMETRY_CONTEXT = {
  requestId: '11111111-1111-4111-8111-111111111111',
  telemetry: { emit: vi.fn() },
} satisfies RequestTelemetryContext

type RegisteredHandlerContext = {
  request: Request
  params: Record<string, string>
  context: RequestTelemetryContext
}

type RouteWithHandlers = {
  options: {
    server?: {
      handlers?: Record<string, (context: RegisteredHandlerContext) => Promise<Response>>
    }
  }
}

type IdentityRequest = {
  method: string
  path: string
  body: unknown
}

const requests: IdentityRequest[] = []
let identityUrl = ''
let acknowledgedErasure = false
let activityAdmissionStatus = 204
let activeClientIp = '198.51.100.10'
let issuedBrowserCapability = `capability_${'a'.repeat(48)}`
let browserCapabilityState: string = 'active'
let issueCapabilityFailure = false
let validateCapabilityFailure = false
let deleteAccountFailure = false
let rateLimitCleanupPool: Pool | undefined
const envBeforeTest = new Map<string, string | undefined>()
const envKeys = [
  'SHIFU_WEB_APP_URL',
  'BETTER_AUTH_DATABASE_URL',
  'BETTER_AUTH_SECRET',
  'SHIFU_BFF_SHARED_SECRET',
  'SHIFU_IDENTITY_API_URL',
  'SHIFU_TRUSTED_PROXY_IPS',
] as const
let profile: IdentityProfile = {
  account_id: ACCOUNT_ID,
  display_name: 'Pessoa Estudante',
  email: 'shifu-98@example.test',
  time_zone: 'America/Sao_Paulo' as string | null,
  appearance: 'dark' as const,
  status: 'active',
  created_at: '2026-11-20T12:00:00Z',
  confirmed_at: '2026-11-20T12:01:00Z' as string | null,
}

const identityServer = createServer((request, response) => {
  void handleIdentityRequest(request, response)
})

async function readJsonBody(request: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = []
  for await (const chunk of request) chunks.push(Buffer.from(chunk))
  if (chunks.length === 0) return undefined
  return JSON.parse(Buffer.concat(chunks).toString('utf8')) as unknown
}

function writeJson(response: ServerResponse, status: number, body: unknown) {
  response.statusCode = status
  response.setHeader('Content-Type', 'application/json')
  response.end(JSON.stringify(body))
}

function writeEmpty(response: ServerResponse, status = 204) {
  response.statusCode = status
  response.end()
}

async function handleIdentityRequest(request: IncomingMessage, response: ServerResponse) {
  const body = await readJsonBody(request)
  const path = request.url ?? ''
  requests.push({ method: request.method ?? '', path, body })

  if (request.method === 'POST' && path === '/identity/sign-in') {
    writeJson(response, 200, {
      profile,
      access: 'protected',
      access_version: 1,
    })
    return
  }

  if (
    request.method === 'POST' &&
    path === '/identity/internal/account-activity-admissions'
  ) {
    if (activityAdmissionStatus === 204) writeEmpty(response)
    else writeJson(response, activityAdmissionStatus, { code: 'identity_unavailable' })
    return
  }

  if (request.method === 'GET' && path === '/identity/session') {
    writeJson(response, 200, {
      account_id: profile.account_id,
      display_name: profile.display_name,
      time_zone: profile.time_zone,
      appearance: profile.appearance,
    })
    return
  }

  if (request.method === 'GET' && path === '/identity/accounts/me') {
    writeJson(response, 200, profile)
    return
  }

  if (request.method === 'PATCH' && path === '/identity/accounts/me') {
    const input = body as {
      display_name: string
      time_zone: string
      appearance: 'dark' | 'light' | 'system'
    }
    profile = {
      ...profile,
      display_name: input.display_name,
      time_zone: input.time_zone,
      appearance: input.appearance,
    }
    writeJson(response, 200, profile)
    return
  }

  if (request.method === 'POST' && path === '/identity/account-deletions') {
    if (deleteAccountFailure) {
      writeJson(response, 503, { code: 'identity_unavailable' })
      return
    }
    writeJson(response, 200, {
      state: 'closed',
      closed_at: CLOSED_AT,
      erasure: 'pending',
    })
    return
  }

  if (request.method === 'POST' && path === '/identity/browser-data-capabilities') {
    if (issueCapabilityFailure) {
      writeJson(response, 503, { code: 'identity_unavailable' })
      return
    }
    writeJson(response, 201, { capability: issuedBrowserCapability })
    return
  }
  if (request.method === 'POST' && path === '/identity/browser-data-validations') {
    if (validateCapabilityFailure) {
      writeJson(response, 503, { code: 'identity_unavailable' })
      return
    }
    writeJson(response, 200, { state: browserCapabilityState })
    return
  }

  const erasurePath = path.match(
    /^\/identity\/internal\/account-erasures\/([^/]+)\/(status|target|acknowledgements)$/,
  )
  if (erasurePath?.[2] === 'status' && request.method === 'GET') {
    writeJson(response, 200, {
      state: 'closed',
      closed_at: CLOSED_AT,
      erasure: acknowledgedErasure ? 'completed' : 'pending',
    })
    return
  }
  if (erasurePath?.[2] === 'target' && request.method === 'GET') {
    writeJson(response, 200, {
      account_id: profile.account_id,
      erasure_id: decodeURIComponent(erasurePath[1] ?? ''),
    })
    return
  }
  if (erasurePath?.[2] === 'acknowledgements' && request.method === 'POST') {
    acknowledgedErasure = true
    writeEmpty(response)
    return
  }

  writeJson(response, 404, { code: 'not_found' })
}

function registeredHandler(route: unknown, method: string) {
  const handler = (route as RouteWithHandlers).options.server?.handlers?.[method]
  if (!handler) throw new Error(`The route must register a ${method} handler.`)
  return handler
}

function collectCookies(response: Response, cookies: Map<string, string>) {
  for (const header of response.headers.getSetCookie()) {
    const pair = header.split(';', 1)[0]
    const separator = pair.indexOf('=')
    if (separator < 0) continue
    cookies.set(pair.slice(0, separator), pair.slice(separator + 1))
  }
}

function cookieHeader(cookies: Map<string, string>) {
  return [...cookies]
    .filter(([, value]) => value.length > 0)
    .map(([name, value]) => `${name}=${value}`)
    .join('; ')
}

function accountActivityLockKey(accountId: string) {
  const bytes = createHash('sha256')
    .update(`shifu:account-activity:v1:${accountId}`, 'utf8')
    .digest()
    .subarray(0, 8)
  return BigInt.asIntN(64, bytes.readBigUInt64BE()).toString()
}

async function callRoute(
  route: unknown,
  method: string,
  path: string,
  options: {
    body?: unknown
    cookies?: Map<string, string>
    headers?: Record<string, string>
    origin?: string
    url?: string
  } = {},
) {
  const headers = new Headers({ Origin: options.origin ?? BASE_URL })
  headers.set('X-Forwarded-For', `${activeClientIp}, 127.0.0.1`)
  for (const [name, value] of Object.entries(options.headers ?? {}))
    headers.set(name, value)
  const cookie = options.cookies ? cookieHeader(options.cookies) : ''
  if (cookie) headers.set('Cookie', cookie)
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')
  const request = new Request(new URL(options.url ?? path, BASE_URL), {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  return registeredHandler(
    route,
    method,
  )({
    request,
    params: {},
    context: TELEMETRY_CONTEXT,
  })
}

describe('registered account authentication HTTP handlers', () => {
  beforeAll(async () => {
    for (const key of envKeys) envBeforeTest.set(key, process.env[key])
    process.env.SHIFU_WEB_APP_URL = BASE_URL
    process.env.BETTER_AUTH_DATABASE_URL ??=
      'postgresql://shifu:shifu-local@127.0.0.1:54344/shifu'
    process.env.BETTER_AUTH_SECRET = 'ci-secret-with-at-least-32-characters-for-tests'
    process.env.SHIFU_BFF_SHARED_SECRET = 'ci-bff-shared-secret'
    process.env.SHIFU_TRUSTED_PROXY_IPS = '127.0.0.1'
    rateLimitCleanupPool = new Pool({
      connectionString: process.env.BETTER_AUTH_DATABASE_URL,
    })
    for (const ipAddress of TEST_CLIENT_IPS) {
      await rateLimitCleanupPool.query(
        'delete from better_auth_rate_limits where key like $1',
        [`${ipAddress}%`],
      )
    }
    await new Promise<void>((resolve) => identityServer.listen(0, '127.0.0.1', resolve))
    identityUrl = `http://127.0.0.1:${(identityServer.address() as AddressInfo).port}`
    process.env.SHIFU_IDENTITY_API_URL = identityUrl
  })

  afterAll(async () => {
    try {
      if (rateLimitCleanupPool) {
        for (const ipAddress of TEST_CLIENT_IPS) {
          await rateLimitCleanupPool.query(
            'delete from better_auth_rate_limits where key like $1',
            [`${ipAddress}%`],
          )
        }
      }
      await Promise.all(trackedPools.map((pool) => pool.end()))
      await new Promise<void>((resolve, reject) =>
        identityServer.close((error) => (error ? reject(error) : resolve())),
      )
    } finally {
      for (const key of envKeys) {
        const previousValue = envBeforeTest.get(key)
        if (previousValue === undefined) delete process.env[key]
        else process.env[key] = previousValue
      }
    }
  })

  it('authenticates, reads and updates the account, then closes it through public routes', async () => {
    activeClientIp = '198.51.100.10'
    requests.length = 0
    acknowledgedErasure = false
    activityAdmissionStatus = 204
    issueCapabilityFailure = false
    validateCapabilityFailure = false
    deleteAccountFailure = false
    profile = {
      account_id: ACCOUNT_ID,
      display_name: 'Pessoa Estudante',
      email: 'shifu-98@example.test',
      time_zone: 'America/Sao_Paulo',
      appearance: 'dark',
      status: 'active',
      created_at: '2026-11-20T12:00:00Z',
      confirmed_at: '2026-11-20T12:01:00Z',
    }
    const cookies = new Map<string, string>()

    const signedIn = await callRoute(authRoute, 'POST', '/api/auth/sign-in/identity', {
      body: { email: profile.email, password: 'current-password' },
      cookies,
    })
    collectCookies(signedIn, cookies)
    expect(signedIn.status).toBe(200)
    expect(await signedIn.json()).toEqual({ access: 'protected', redirectTo: '/' })
    expect(cookieHeader(cookies)).not.toBe('')

    const account = await callRoute(authRoute, 'GET', '/api/auth/account', { cookies })
    expect(account.status).toBe(200)
    expect(account.headers.get('cache-control')).toBe('no-store')
    expect(await account.json()).toEqual({
      accountId: ACCOUNT_ID,
      displayName: 'Pessoa Estudante',
      email: 'shifu-98@example.test',
      timeZone: 'America/Sao_Paulo',
      appearance: 'dark',
    })

    const updated = await callRoute(authRoute, 'POST', '/api/auth/account/profile', {
      body: {
        displayName: 'Pessoa Atualizada',
        timeZone: 'UTC',
        appearance: 'light',
      },
      cookies,
    })
    expect(updated.status).toBe(200)
    expect(await updated.json()).toMatchObject({
      displayName: 'Pessoa Atualizada',
      timeZone: 'UTC',
      appearance: 'light',
    })

    const issuedCapability = await callRoute(
      browserCapabilityRoute,
      'POST',
      '/api/identity/browser-data-capabilities',
      { body: {}, cookies },
    )
    expect(issuedCapability.status).toBe(201)
    const { capability } = (await issuedCapability.json()) as { capability: string }
    expect(capability).toMatch(/^[A-Za-z0-9_-]{32,256}$/)

    const validatedCapability = await callRoute(
      browserCapabilityValidationRoute,
      'POST',
      '/api/identity/browser-data-validations',
      { body: { capability }, cookies },
    )
    expect(validatedCapability.status).toBe(200)
    expect(await validatedCapability.json()).toEqual({ state: 'active' })

    const secureCapability = await callRoute(
      browserCapabilityRoute,
      'POST',
      '/api/identity/browser-data-capabilities',
      {
        body: {},
        cookies,
        origin: 'https://127.0.0.1:7000',
        url: 'https://127.0.0.1:7000/api/identity/browser-data-capabilities',
      },
    )
    expect(secureCapability.status).toBe(201)

    issuedBrowserCapability = 'invalid'
    const invalidIssuedCapability = await callRoute(
      browserCapabilityRoute,
      'POST',
      '/api/identity/browser-data-capabilities',
      { body: {}, cookies },
    )
    browserCapabilityState = 'unknown'
    const invalidValidationState = await callRoute(
      browserCapabilityValidationRoute,
      'POST',
      '/api/identity/browser-data-validations',
      { body: { capability }, cookies },
    )
    issuedBrowserCapability = `capability_${'a'.repeat(48)}`
    browserCapabilityState = 'active'
    issueCapabilityFailure = true
    const unavailableCapability = await callRoute(
      browserCapabilityRoute,
      'POST',
      '/api/identity/browser-data-capabilities',
      { body: {}, cookies },
    )
    issueCapabilityFailure = false
    expect(invalidIssuedCapability.status).toBe(503)
    expect(invalidValidationState.status).toBe(503)
    expect(unavailableCapability.status).toBe(503)

    const prepared = await callRoute(
      accountDeletionPrepareRoute,
      'POST',
      '/api/auth/account/deletion/prepare',
      { body: {}, cookies },
    )
    collectCookies(prepared, cookies)
    expect(prepared.status).toBe(201)
    expect(await prepared.json()).toEqual({ state: 'prepared' })

    const closed = await callRoute(
      accountDeletionRoute,
      'POST',
      '/api/auth/account/deletion',
      { body: { currentPassword: 'current-password', confirmed: true }, cookies },
    )
    collectCookies(closed, cookies)
    expect(closed.status).toBe(202)
    expect(await closed.json()).toEqual({
      state: 'closed',
      closedAt: CLOSED_AT,
      erasure: 'completed',
    })

    expect(requests.map(({ path }) => path)).toContain(
      '/identity/internal/account-activity-admissions',
    )
    expect(
      requests.some(({ path }) =>
        /^\/identity\/internal\/account-erasures\/[^/]+\/status$/.test(path),
      ),
    ).toBe(true)
    expect(
      requests.some(
        ({ path, body }) =>
          path === '/identity/internal/account-activity-admissions' &&
          (body as { session_id?: string }).session_id !== undefined,
      ),
    ).toBe(true)
  })

  it('keeps account deletion fail closed when Identity is unavailable', async () => {
    activeClientIp = '198.51.100.18'
    requests.length = 0
    acknowledgedErasure = false
    activityAdmissionStatus = 204
    validateCapabilityFailure = false
    deleteAccountFailure = false
    profile = {
      account_id: '01J00000000000000000000105',
      display_name: 'Pessoa em exclusão',
      email: 'shifu-98-unavailable@example.test',
      time_zone: 'America/Sao_Paulo',
      appearance: 'system',
      status: 'active',
      created_at: '2026-11-20T12:00:00Z',
      confirmed_at: '2026-11-20T12:01:00Z',
    }
    const cookies = new Map<string, string>()
    const signedIn = await callRoute(authRoute, 'POST', '/api/auth/sign-in/identity', {
      body: { email: profile.email, password: 'current-password' },
      cookies,
    })
    collectCookies(signedIn, cookies)
    expect(signedIn.status).toBe(200)

    validateCapabilityFailure = true
    const unavailableValidation = await callRoute(
      browserCapabilityValidationRoute,
      'POST',
      '/api/identity/browser-data-validations',
      { body: { capability: `capability_${'a'.repeat(48)}` }, cookies },
    )
    validateCapabilityFailure = false
    expect(unavailableValidation.status).toBe(503)

    const prepared = await callRoute(
      accountDeletionPrepareRoute,
      'POST',
      '/api/auth/account/deletion/prepare',
      { body: {}, cookies },
    )
    collectCookies(prepared, cookies)
    expect(prepared.status).toBe(201)

    deleteAccountFailure = true
    const unavailableDeletion = await callRoute(
      accountDeletionRoute,
      'POST',
      '/api/auth/account/deletion',
      { body: { currentPassword: 'current-password', confirmed: true }, cookies },
    )
    deleteAccountFailure = false
    expect(unavailableDeletion.status).toBe(503)
  })

  it('reconciles a pending erasure through the registered status route', async () => {
    activeClientIp = '198.51.100.11'
    const erasureAccountId = '01J00000000000000000000099'
    requests.length = 0
    acknowledgedErasure = false
    activityAdmissionStatus = 204
    profile = {
      account_id: erasureAccountId,
      display_name: 'Pessoa em recuperação',
      email: 'shifu-98-recovery@example.test',
      time_zone: 'America/Sao_Paulo',
      appearance: 'system',
      status: 'active',
      created_at: '2026-11-20T12:00:00Z',
      confirmed_at: '2026-11-20T12:01:00Z',
    }
    const cookies = new Map<string, string>()

    const signedIn = await callRoute(authRoute, 'POST', '/api/auth/sign-in/identity', {
      body: { email: profile.email, password: 'current-password' },
      cookies,
    })
    collectCookies(signedIn, cookies)
    expect(signedIn.status).toBe(200)

    const unpreparedDeletion = await callRoute(
      accountDeletionRoute,
      'POST',
      '/api/auth/account/deletion',
      { body: { currentPassword: 'current-password', confirmed: true }, cookies },
    )
    expect(unpreparedDeletion.status).toBe(403)
    const missingStatusCookie = await callRoute(
      accountDeletionRoute,
      'GET',
      '/api/auth/account/deletion',
      { cookies },
    )
    expect(missingStatusCookie.status).toBe(403)

    const prepared = await callRoute(
      accountDeletionPrepareRoute,
      'POST',
      '/api/auth/account/deletion/prepare',
      { body: {}, cookies },
    )
    collectCookies(prepared, cookies)
    expect(prepared.status).toBe(201)

    const activeProfile = profile
    profile = { ...profile, account_id: '01J00000000000000000000104' }
    const mismatchedIdentity = await callRoute(
      accountDeletionRoute,
      'POST',
      '/api/auth/account/deletion',
      { body: { currentPassword: 'current-password', confirmed: true }, cookies },
    )
    profile = activeProfile
    expect(mismatchedIdentity.status).toBe(401)

    const status = await callRoute(
      accountDeletionRoute,
      'GET',
      '/api/auth/account/deletion',
      { cookies },
    )

    expect(status.status).toBe(200)
    expect(await status.json()).toEqual({
      state: 'closed',
      closedAt: CLOSED_AT,
      erasure: 'completed',
    })
    expect(
      requests.some(({ path }) =>
        /^\/identity\/internal\/account-erasures\/[^/]+\/target$/.test(path),
      ),
    ).toBe(true)
    expect(requests.some(({ path }) => path.endsWith('/acknowledgements'))).toBe(true)
  })

  it('rejects unsupported methods and malformed capabilities before calling Identity', async () => {
    activeClientIp = '198.51.100.12'
    requests.length = 0
    const invalidOrigin = await callRoute(
      browserCapabilityRoute,
      'POST',
      '/api/identity/browser-data-capabilities',
      { body: {}, origin: 'https://attacker.example' },
    )
    const missingOrigin = await callRoute(
      browserCapabilityRoute,
      'POST',
      '/api/identity/browser-data-capabilities',
      { body: {}, origin: '' },
    )
    const invalidCapability = await callRoute(
      browserCapabilityValidationRoute,
      'POST',
      '/api/identity/browser-data-validations',
      { body: { capability: 'short' } },
    )
    const insecureValidation = await callRoute(
      browserCapabilityValidationRoute,
      'POST',
      '/api/identity/browser-data-validations',
      {
        body: { capability: `capability_${'a'.repeat(48)}` },
        url: 'http://external.example/api/identity/browser-data-validations',
      },
    )
    const unauthorized = await callRoute(
      browserCapabilityRoute,
      'POST',
      '/api/identity/browser-data-capabilities',
      { body: {}, cookies: new Map() },
    )

    expect(invalidOrigin.status).toBe(403)
    expect(missingOrigin.status).toBe(403)
    expect(invalidCapability.status).toBe(400)
    expect(insecureValidation.status).toBe(403)
    expect(unauthorized.status).toBe(401)
    expect(requests).toHaveLength(0)
  })

  it('fails closed when Identity rejects or cannot validate account activity', async () => {
    activeClientIp = '198.51.100.13'
    const activityAccountId = '01J00000000000000000000100'
    requests.length = 0
    acknowledgedErasure = false
    activityAdmissionStatus = 204
    profile = {
      account_id: activityAccountId,
      display_name: 'Pessoa com atividade protegida',
      email: 'shifu-98-activity@example.test',
      time_zone: 'America/Sao_Paulo',
      appearance: 'system',
      status: 'active',
      created_at: '2026-11-20T12:00:00Z',
      confirmed_at: '2026-11-20T12:01:00Z',
    }
    const cookies = new Map<string, string>()
    const signedIn = await callRoute(authRoute, 'POST', '/api/auth/sign-in/identity', {
      body: { email: profile.email, password: 'current-password' },
      cookies,
    })
    collectCookies(signedIn, cookies)
    expect(signedIn.status).toBe(200)

    const activeProfile = profile
    profile = { ...profile, account_id: '01J00000000000000000000103' }
    const identityMismatch = await callRoute(
      accountDeletionPrepareRoute,
      'POST',
      '/api/auth/account/deletion/prepare',
      { body: {}, cookies },
    )
    profile = activeProfile

    const signInAdmission = requests.find(
      ({ path }) => path === '/identity/internal/account-activity-admissions',
    )
    const admittedAccountId = (
      signInAdmission?.body as { account_id?: unknown } | undefined
    )?.account_id
    if (typeof admittedAccountId !== 'string') {
      throw new Error('Sign-in did not admit account activity.')
    }
    const lockPool = new Pool({
      connectionString: process.env.BETTER_AUTH_DATABASE_URL,
    })
    const lockClient = await lockPool.connect()
    const lockKey = accountActivityLockKey(admittedAccountId)
    await lockClient.query('SELECT pg_advisory_lock($1::bigint)', [lockKey])
    activityAdmissionStatus = 204
    const lockTimeout = await (async () => {
      try {
        return await callRoute(authRoute, 'GET', '/api/auth/account', { cookies })
      } finally {
        await lockClient.query('SELECT pg_advisory_unlock($1::bigint)', [lockKey])
        lockClient.release()
      }
    })()

    activityAdmissionStatus = 503
    const unavailable = await callRoute(authRoute, 'GET', '/api/auth/account', {
      cookies,
    })
    activityAdmissionStatus = 401
    const rejected = await callRoute(authRoute, 'GET', '/api/auth/account', { cookies })

    expect(unavailable.status).toBe(503)
    expect(rejected.status).toBe(401)
    expect(identityMismatch.status).toBe(401)
    expect(lockTimeout.status).toBe(503)
    expect(
      requests.filter(
        ({ path }) => path === '/identity/internal/account-activity-admissions',
      ),
    ).toHaveLength(3)
  }, 10_000)

  it('authenticates the internal account-closure callback and reconciles its target', async () => {
    activeClientIp = '198.51.100.14'
    const erasureAccountId = '01J00000000000000000000101'
    const erasureId = '11111111-1111-4111-8111-111111111111'
    requests.length = 0
    acknowledgedErasure = false
    profile = {
      account_id: erasureAccountId,
      display_name: 'Pessoa encerrada',
      email: 'shifu-98-callback@example.test',
      time_zone: 'America/Sao_Paulo',
      appearance: 'system',
      status: 'active',
      created_at: '2026-11-20T12:00:00Z',
      confirmed_at: '2026-11-20T12:01:00Z',
    }
    const missingSecret = await callRoute(
      accountClosureRoute,
      'POST',
      '/api/internal/identity/account-closure',
      { body: { account_id: erasureAccountId, erasure_id: erasureId } },
    )
    const invalidBody = await callRoute(
      accountClosureRoute,
      'POST',
      '/api/internal/identity/account-closure',
      {
        body: { account_id: erasureAccountId, erasure_id: 'invalid' },
        headers: { 'X-Shifu-Bff-Secret': 'ci-bff-shared-secret' },
      },
    )
    const mismatchedTarget = await callRoute(
      accountClosureRoute,
      'POST',
      '/api/internal/identity/account-closure',
      {
        body: {
          account_id: '01J00000000000000000000102',
          erasure_id: erasureId,
        },
        headers: { 'X-Shifu-Bff-Secret': 'ci-bff-shared-secret' },
      },
    )
    const closed = await callRoute(
      accountClosureRoute,
      'POST',
      '/api/internal/identity/account-closure',
      {
        body: { account_id: erasureAccountId, erasure_id: erasureId },
        headers: { 'X-Shifu-Bff-Secret': 'ci-bff-shared-secret' },
      },
    )

    expect(missingSecret.status).toBe(401)
    expect(invalidBody.status).toBe(400)
    expect(mismatchedTarget.status).toBe(503)
    expect(closed.status).toBe(200)
    expect(await closed.json()).toEqual({ closed: true })
    expect(
      requests.some(
        ({ path }) =>
          path === `/identity/internal/account-erasures/${erasureId}/acknowledgements`,
      ),
    ).toBe(true)
  })
})
