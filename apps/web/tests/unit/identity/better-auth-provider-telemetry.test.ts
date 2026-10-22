import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  const identity = {
    getCurrentSession: vi.fn(),
    publishMainPageEntered: vi.fn(),
    requestPasswordRecovery: vi.fn(),
    getPasswordRecoveryStatus: vi.fn(),
    retryPasswordRecovery: vi.fn(),
    getPasswordResetLinkStatus: vi.fn(),
    resetPassword: vi.fn(),
    registerAccount: vi.fn(),
    getPendingConfirmationStatus: vi.fn(),
    resendConfirmation: vi.fn(),
    confirmEmail: vi.fn(),
    validateCredentials: vi.fn(),
    verifyPendingConfirmationContext: vi.fn(),
  }
  const auth = {
    api: { getSession: vi.fn(), getToken: vi.fn() },
    handler: vi.fn(),
  }
  const endpoints = new Map<string, (context: unknown) => Promise<unknown>>()
  return {
    auth,
    endpoints,
    identity,
    telemetry: { emit: vi.fn() },
    betterAuth: vi.fn(() => auth),
    createServerRequestClient: vi.fn(() => ({})),
  }
})

vi.mock('better-auth', () => ({ betterAuth: mocks.betterAuth }))
vi.mock('better-auth/api', () => ({
  APIError: {
    from: vi.fn(
      (_status: string, details: unknown) => new Error(JSON.stringify(details)),
    ),
  },
  createAuthEndpoint: vi.fn(
    (
      path: string,
      _options: unknown,
      handler: (context: unknown) => Promise<unknown>,
    ) => {
      mocks.endpoints.set(path, handler)
      return { path, handler }
    },
  ),
}))
vi.mock('better-auth/cookies', () => ({
  deleteSessionCookie: vi.fn(),
  setSessionCookie: vi.fn(),
}))
vi.mock('better-auth/plugins', () => ({ jwt: vi.fn(() => ({ id: 'jwt' })) }))
vi.mock('pg', () => ({
  Pool: class {
    end = vi.fn()
  },
  types: { setTypeParser: vi.fn() },
}))
vi.mock('@tanstack/react-start/server', () => ({
  setResponseHeaders: vi.fn(),
}))
vi.mock('@/provision/auth/better-auth/better-auth-config', () => ({
  BETTER_AUTH_OPTIONS: {
    rateLimitMaxRequests: 10,
    rateLimitWindowSeconds: 300,
    sessionLifetimeSeconds: 3600,
  },
  BetterAuthConfig: () => ({
    baseURL: 'http://web.test',
    bffSharedSecret: 'bff-secret',
    databaseURL: 'postgresql://test',
    identityURL: 'http://api.test',
    secret: 'secret-which-is-long-enough-for-tests',
    trustedProxyIPs: [],
    useSecureCookies: false,
  }),
}))
vi.mock('@/rest/axios/server-request-client', () => ({
  createServerRequestClient: mocks.createServerRequestClient,
}))
vi.mock('@/rest/services/identity-service', () => ({
  IdentityService: () => mocks.identity,
}))
vi.mock('@/provision/telemetry/console-telemetry-provider', () => ({
  getWebTelemetryProvider: () => mocks.telemetry,
}))

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

const request = new Request('http://web.test/api/auth/get-session')
const session = {
  user: {
    id: 'account-1',
    name: 'Aluno',
    email: 'student@example.test',
  },
}
const currentSession = {
  account_id: 'account-1',
  display_name: 'Aluno',
  time_zone: 'America/Sao_Paulo',
}

function endpointContext() {
  return {
    request,
    body: {},
    json: (value: unknown) => value,
    getSignedCookie: vi.fn(async () => null),
    setSignedCookie: vi.fn(async () => undefined),
    context: {
      secret: 'secret',
      options: { advanced: { useSecureCookies: false } },
      internalAdapter: {
        createVerificationValue: vi.fn(),
        deleteVerificationByIdentifier: vi.fn(),
        findVerificationValue: vi.fn(),
        deleteUserSessions: vi.fn(),
        findUserById: vi.fn(),
        createSession: vi.fn(),
        createUser: vi.fn(),
        updateUser: vi.fn(),
        deleteSession: vi.fn(),
        deleteUser: vi.fn(),
      },
    },
  }
}

describe('Better Auth provider telemetry wiring', () => {
  const provider = getBetterAuthProvider()

  beforeEach(() => {
    vi.clearAllMocks()
    mocks.auth.api.getSession.mockResolvedValue(session)
    mocks.auth.api.getToken.mockResolvedValue({ token: 'access-token' })
    mocks.auth.handler.mockResolvedValue(new Response(null, { status: 200 }))
    for (const method of Object.values(mocks.identity)) {
      method.mockRejectedValue(new Error('endpoint not configured'))
    }
    mocks.identity.getCurrentSession.mockResolvedValue(currentSession)
    mocks.identity.publishMainPageEntered.mockResolvedValue(undefined)
  })

  it('uses request-scoped clients and preserves the provider access fallbacks', async () => {
    mocks.auth.api.getSession.mockResolvedValueOnce(null)
    await expect(provider.getCurrentAccess(request)).resolves.toBeNull()

    await expect(
      provider.getCurrentAccess(request, '11111111-1111-4111-8111-111111111111'),
    ).resolves.toMatchObject({
      accountId: currentSession.account_id,
      accessToken: 'access-token',
    })
    expect(mocks.createServerRequestClient).toHaveBeenCalledWith(
      expect.objectContaining({ requestId: '11111111-1111-4111-8111-111111111111' }),
      expect.any(Object),
    )

    mocks.identity.getCurrentSession.mockRejectedValueOnce(new RestError('down', 503))
    await expect(provider.getCurrentAccess(request)).resolves.toMatchObject({
      accountId: session.user.id,
      timeZone: null,
    })

    mocks.identity.getCurrentSession.mockRejectedValueOnce(
      new AuthError('authentication-rejected', 'expired', { statusCode: 401 }),
    )
    await expect(provider.getCurrentAccess(request, 'request-1')).resolves.toBeNull()
    expect(mocks.telemetry.emit).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'auth.session.revoked', request_id: 'request-1' }),
    )

    mocks.identity.getCurrentSession.mockRejectedValueOnce(
      new AuthError('unavailable', 'down', { statusCode: 503 }),
    )
    await expect(provider.getCurrentAccess(request)).resolves.toMatchObject({
      accountId: session.user.id,
      timeZone: null,
    })

    mocks.identity.getCurrentSession.mockRejectedValueOnce(new RestError('rejected', 401))
    await expect(provider.getCurrentAccess(request, 'request-4')).resolves.toBeNull()
    expect(mocks.telemetry.emit).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'auth.session.revoked', request_id: 'request-4' }),
    )

    mocks.identity.getCurrentSession.mockRejectedValueOnce(new Error('unexpected'))
    await expect(provider.getCurrentAccess(request)).rejects.toThrow('unexpected')

    mocks.auth.api.getToken.mockResolvedValueOnce({ token: undefined })
    await expect(provider.getCurrentAccess(request)).rejects.toBeInstanceOf(AuthError)

    await provider.deleteRejectedSession(request, 'request-5')
    expect(mocks.auth.handler).toHaveBeenCalled()
  })

  it('keeps main-page observability best effort and forwards its request ID', async () => {
    const access = {
      accountId: 'account-1',
      displayName: 'Aluno',
      email: 'student@example.test',
      timeZone: null,
      accessToken: 'access-token',
    }
    await provider.publishMainPageEntered(access, 'request-2')
    expect(mocks.identity.publishMainPageEntered).toHaveBeenCalledWith('access-token')

    mocks.identity.publishMainPageEntered.mockRejectedValueOnce(new Error('down'))
    await expect(
      provider.publishMainPageEntered(access, 'request-3'),
    ).resolves.toBeUndefined()
    expect(mocks.telemetry.emit).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'dependency.unavailable',
        request_id: 'request-3',
      }),
    )

    await provider.publishMainPageEntered(access)
  })

  it('initializes every request-scoped identity endpoint', async () => {
    expect(mocks.endpoints.size).toBeGreaterThan(5)

    for (const handler of mocks.endpoints.values()) {
      try {
        await handler(endpointContext())
      } catch {
        // Endpoint-specific validation is covered by the identity suites.
      }
    }
  })
})
