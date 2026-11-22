import { setResponseHeaders } from '@tanstack/react-start/server'
import { createHmac, randomUUID, timingSafeEqual } from 'node:crypto'
import {
  betterAuth,
  type BetterAuthPlugin,
  type GenericEndpointContext,
} from 'better-auth'
import { APIError, createAuthEndpoint, getSessionFromCtx } from 'better-auth/api'
import { deleteSessionCookie, setSessionCookie } from 'better-auth/cookies'
import { jwt } from 'better-auth/plugins'
import { Pool, types as pgTypes } from 'pg'
import { z } from 'zod'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { ROUTES } from '@/constants/routes'
import { AuthError } from '@/core/errors/auth-error'
import {
  ACCOUNT_APPEARANCES,
  type AccountAppearance,
} from '@/core/identity/account-appearance'
import { RestError } from '@/core/errors/rest-error'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import {
  createServerRequestClient,
  type ServerRequestClientOptions,
} from '@/rest/axios/server-request-client'
import {
  IdentityService,
  type AccountErasureResult,
} from '@/rest/services/identity-service'
import { getWebTelemetryProvider } from '@/provision/telemetry/console-telemetry-provider'
import { AccountActivityScope } from '@/provision/auth/account-activity-scope'

import { BETTER_AUTH_OPTIONS, BetterAuthConfig } from './better-auth-config'

const PENDING_COOKIE_NAME = 'shifu-pending-flow'
const PENDING_FLOW_LIFETIME_SECONDS = 15 * 60
const PENDING_FLOW_LIFETIME_MS = PENDING_FLOW_LIFETIME_SECONDS * 1000
const PASSWORD_RECOVERY_COOKIE_NAME = 'shifu-password-recovery'
const PASSWORD_RECOVERY_LIFETIME_SECONDS = 60 * 60
const PASSWORD_RECOVERY_LIFETIME_MS = PASSWORD_RECOVERY_LIFETIME_SECONDS * 1000
const PASSWORD_RECOVERY_COOLDOWN_MS = 60 * 1000
const ACCOUNT_ERASURE_COOKIE_NAME = 'shifu-account-erasure'
const ACCOUNT_ERASURE_COOKIE_LIFETIME_SECONDS = 24 * 60 * 60
const ACCOUNT_ERASURE_FIRST_CONFIRMATION_LIFETIME_MS = 15 * 60 * 1000

export type LayoutAccount = {
  displayName: string
  email: string
  appearance: AccountAppearance
}

const signInBody = z.object({
  email: z.string().min(1),
  password: z.string().min(1),
})

const registerBody = z.object({
  displayName: z.string().min(1),
  email: z.string().min(1),
  password: z.string().min(8),
})

const confirmEmailBody = z.object({ token: z.string().min(1) })
const passwordRecoveryBody = z.object({ email: z.string().min(1) })
const passwordResetBody = z.object({
  password: z.string().min(1),
  passwordConfirmation: z.string().min(1),
  token: z.string().optional().default(''),
})
const passwordResetLinkBody = z.object({ token: z.string().optional().default('') })
const accountDeletionBody = z
  .object({ currentPassword: z.string().min(1), confirmed: z.literal(true) })
  .strict()

type AccountErasureCookie = {
  erasureId: string
  actorBinding: string
  firstConfirmationExpiresAt: number
  expiresAt: number
}

const telemetry = getWebTelemetryProvider()

type ServerAuthenticatedAccess = {
  accountId: string
  displayName: string
  email: string
  timeZone: string | null
  appearance: AccountAppearance
  accessToken: string
}

const BetterAuthProvider = () => {
  const config = BetterAuthConfig()
  pgTypes.setTypeParser(20, (value) => Number.parseInt(value, 10))
  const pool = new Pool({ connectionString: config.databaseURL })
  const activityPool = new Pool({
    connectionString: config.databaseURL,
    max: 4,
    connectionTimeoutMillis: 5000,
  })
  const accountActivityScope = new AccountActivityScope(activityPool)
  const authPool = accountActivityScope.createPinnedAuthPool(pool)
  const identityClientOptions = {
    baseUrl: config.identityURL,
    defaultHeaders: { 'X-Shifu-Bff-Secret': config.bffSharedSecret },
    withCredentials: false,
  } satisfies ServerRequestClientOptions
  const identityService = createIdentityService()

  function createIdentityService(requestId?: string) {
    const requestContext: RequestTelemetryContext | undefined = requestId
      ? { requestId, telemetry }
      : undefined
    return IdentityService(
      createServerRequestClient(requestContext, identityClientOptions),
    )
  }

  const requestIdentityService = (request?: Request) =>
    createIdentityService(request?.headers.get('X-Request-ID') ?? undefined)
  const identityPlugin = createIdentityPlugin(
    requestIdentityService,
    async (headers) => {
      const result = await auth.api.getToken({ headers })
      if (!result?.token)
        throw APIError.from('UNAUTHORIZED', {
          code: 'unauthorized',
          message: 'Entre novamente para continuar.',
        })
      return result.token
    },
    withAccountActivity,
    closeTechnicalAccountAfterIdentityClosure,
  )
  const auth = betterAuth({
    appName: 'Shifu',
    baseURL: config.baseURL,
    basePath: '/api/auth',
    secret: config.secret,
    database: authPool,
    emailAndPassword: { enabled: false },
    disabledPaths: ['/update-session', '/update-user', '/change-password'],
    user: {
      modelName: 'better_auth_users',
      fields: {
        emailVerified: 'email_verified',
        createdAt: 'created_at',
        updatedAt: 'updated_at',
      },
    },
    session: {
      modelName: 'better_auth_sessions',
      expiresIn: BETTER_AUTH_OPTIONS.sessionLifetimeSeconds,
      updateAge: 0,
      disableSessionRefresh: true,
      fields: {
        userId: 'user_id',
        expiresAt: 'expires_at',
        ipAddress: 'ip_address',
        userAgent: 'user_agent',
        createdAt: 'created_at',
        updatedAt: 'updated_at',
      },
      additionalFields: {
        accessVersion: {
          type: 'number',
          required: true,
          fieldName: 'access_version',
          input: false,
        },
      },
    },
    account: {
      modelName: 'better_auth_accounts',
      fields: {
        accountId: 'account_id',
        providerId: 'provider_id',
        userId: 'user_id',
        accessToken: 'access_token',
        refreshToken: 'refresh_token',
        idToken: 'id_token',
        accessTokenExpiresAt: 'access_token_expires_at',
        refreshTokenExpiresAt: 'refresh_token_expires_at',
        createdAt: 'created_at',
        updatedAt: 'updated_at',
      },
    },
    plugins: [
      identityPlugin,
      jwt({
        jwks: {
          keyPairConfig: { alg: 'EdDSA', crv: 'Ed25519' },
          rotationInterval: 30 * 24 * 60 * 60,
          gracePeriod: 24 * 60 * 60,
        },
        jwt: {
          issuer: config.baseURL,
          audience: 'shifu-api',
          expirationTime: '5 minutes',
          definePayload: ({ session }) => ({
            jti: crypto.randomUUID(),
            sid: session.id,
            access_version: session.accessVersion,
          }),
        },
        schema: {
          jwks: {
            modelName: 'better_auth_jwks',
            fields: {
              publicKey: 'public_key',
              privateKey: 'private_key',
              createdAt: 'created_at',
              expiresAt: 'expires_at',
            },
          },
        },
      }),
    ],
    verification: {
      modelName: 'better_auth_verifications',
      fields: {
        expiresAt: 'expires_at',
        createdAt: 'created_at',
        updatedAt: 'updated_at',
      },
    },
    rateLimit: {
      enabled: true,
      window: BETTER_AUTH_OPTIONS.rateLimitWindowSeconds,
      max: BETTER_AUTH_OPTIONS.rateLimitMaxRequests,
      storage: 'database',
      modelName: 'better_auth_rate_limits',
      fields: {
        lastRequest: 'last_request',
      },
      customRules: {
        '/sign-in/identity': {
          window: BETTER_AUTH_OPTIONS.rateLimitWindowSeconds,
          max: BETTER_AUTH_OPTIONS.rateLimitMaxRequests,
        },
        '/get-session': false,
        '/jwks': false,
        '/pending-confirmation/sign-out': false,
        '/password-recovery': false,
        '/password-recovery/status': false,
        '/password-recovery/retry': false,
        '/password-reset': false,
        '/password-reset-link/status': false,
        '/sign-out': false,
        '/token': false,
      },
    },
    advanced: {
      useSecureCookies: config.useSecureCookies,
      ipAddress: {
        // Forwarded headers are considered only when the deployment names its
        // actual ingress addresses. With no configured proxy, Better Auth
        // fails closed instead of accepting a browser-supplied client IP.
        ipAddressHeaders: config.trustedProxyIPs.length > 0 ? ['x-forwarded-for'] : [],
        trustedProxies: config.trustedProxyIPs,
      },
    },
  })

  async function getCurrentAccess(
    request: Request,
    requestId?: string,
  ): Promise<ServerAuthenticatedAccess | null> {
    const session = await auth.api.getSession({ headers: request.headers })
    if (!session) return null

    const token = await auth.api.getToken({ headers: request.headers })
    const accessToken = token?.token
    if (!accessToken) throw new AuthError('invalid-response', 'Token ausente.')

    try {
      const currentIdentityService = requestId
        ? createIdentityService(requestId)
        : identityService
      const currentSession = await currentIdentityService.getCurrentSession(accessToken)
      if (session.user.id !== currentSession.account_id) {
        await deleteSession(request, requestId)
        return null
      }
      if (session.user.name !== currentSession.display_name) {
        try {
          const context = await auth.$context
          await withAccountActivity(
            currentSession.account_id,
            session.session.accessVersion,
            () =>
              context.internalAdapter.updateUser(session.user.id, {
                name: currentSession.display_name,
              }),
            request,
            session.session.id,
          )
        } catch {
          throw new AuthError(
            'unavailable',
            'Não foi possível validar sua conta agora. Tente novamente.',
          )
        }
      }
      return {
        accountId: currentSession.account_id,
        displayName: currentSession.display_name,
        email: session.user.email,
        timeZone: currentSession.time_zone,
        appearance: currentSession.appearance,
        accessToken,
      }
    } catch (error) {
      if (
        (error instanceof AuthError && error.kind === 'unavailable') ||
        (error instanceof RestError &&
          (error.statusCode === 0 ||
            error.statusCode === 429 ||
            error.statusCode >= 500)) ||
        (error instanceof APIError && error.status === 'SERVICE_UNAVAILABLE')
      ) {
        return null
      }

      if (
        error instanceof AuthError &&
        (error.kind === 'authentication-rejected' || error.kind === 'invalid-response')
      ) {
        await deleteSession(request, requestId)
        return null
      }

      if (error instanceof RestError && error.statusCode === 401) {
        await deleteSession(request, requestId)
        return null
      }

      if (error instanceof APIError && error.status === 'UNAUTHORIZED') {
        await deleteSession(request, requestId)
        return null
      }

      if (error instanceof RestError) {
        return null
      }

      if (error instanceof APIError) {
        return null
      }

      throw error
    }
  }

  async function deleteSession(request: Request, requestId?: string) {
    const response = await auth.handler(
      new Request(new URL('/api/auth/sign-out', request.url), {
        method: 'POST',
        headers: request.headers,
      }),
    )
    const setCookie = response.headers.get('set-cookie')
    if (setCookie) setResponseHeaders(new Headers({ 'set-cookie': setCookie }))
    telemetry.emit({
      level: 'INFO',
      event: 'auth.session.revoked',
      request_id: requestId,
      operation: 'auth.session.revoke',
      result: 'success',
    })
  }

  async function publishMainPageEntered(
    access: ServerAuthenticatedAccess,
    requestId?: string,
  ) {
    try {
      await (requestId
        ? createIdentityService(requestId)
        : identityService
      ).publishMainPageEntered(access.accessToken)
    } catch {
      // Observability is best effort. The access decision has already
      // completed and must not block a valid dashboard navigation.
      telemetry.emit({
        level: 'WARNING',
        event: 'dependency.unavailable',
        request_id: requestId,
        operation: 'dependency.check',
        dependency: 'better-auth',
        result: 'unavailable',
      })
    }
  }

  async function handleIssueBrowserDataCapability(request: Request): Promise<Response> {
    if (request.method !== 'POST' || !isSameOriginRequest(request)) {
      return jsonResponse({ code: 'invalid_request' }, 403)
    }

    let session: Awaited<ReturnType<typeof auth.api.getSession>>
    try {
      session = await auth.api.getSession({ headers: request.headers })
    } catch {
      return jsonResponse({ code: 'identity_unavailable' }, 503)
    }
    if (!session) return jsonResponse({ code: 'unauthorized' }, 401)

    try {
      const token = await auth.api.getToken({ headers: request.headers })
      if (!token?.token) return jsonResponse({ code: 'unauthorized' }, 401)

      const currentIdentity = await requestIdentityService(request).getCurrentSession(
        token.token,
      )
      if (currentIdentity.account_id !== session.user.id) {
        return jsonResponse({ code: 'unauthorized' }, 401)
      }

      const result = await requestIdentityService(request).issueBrowserDataCapability(
        token.token,
      )
      if (!isValidBrowserCapability(result.capability)) {
        return jsonResponse({ code: 'identity_unavailable' }, 503)
      }
      return jsonResponse({ capability: result.capability }, 201)
    } catch {
      return jsonResponse({ code: 'identity_unavailable' }, 503)
    }
  }

  async function handleValidateBrowserDataCapability(
    request: Request,
  ): Promise<Response> {
    if (request.method !== 'POST' || !isSecureRequest(request, config.baseURL)) {
      return jsonResponse({ code: 'invalid_request' }, 403)
    }

    const body = await request.json().catch(() => null)
    const parsedBody = z
      .object({ capability: z.string().min(32).max(256) })
      .strict()
      .safeParse(body)
    if (!parsedBody.success) return jsonResponse({ code: 'invalid_request' }, 400)

    try {
      const status = await requestIdentityService(request).validateBrowserDataCapability(
        parsedBody.data.capability,
      )
      if (status.state !== 'active' && status.state !== 'revoked') {
        return jsonResponse({ code: 'identity_unavailable' }, 503)
      }
      return jsonResponse({ state: status.state })
    } catch {
      return jsonResponse({ code: 'identity_unavailable' }, 503)
    }
  }

  async function handleCloseTechnicalIdentity(request: Request): Promise<Response> {
    if (
      request.method !== 'POST' ||
      !isSecretMatch(request.headers.get('X-Shifu-Bff-Secret'), config.bffSharedSecret)
    ) {
      return jsonResponse({ code: 'unauthorized' }, 401)
    }

    const body = await request.json().catch(() => null)
    const parsedBody = z
      .object({ account_id: z.string().min(1), erasure_id: z.string().uuid() })
      .strict()
      .safeParse(body)
    if (!parsedBody.success) return jsonResponse({ code: 'invalid_request' }, 400)

    const { account_id: accountId, erasure_id: erasureId } = parsedBody.data
    try {
      const identityService = requestIdentityService(request)
      await closeTechnicalAccountAfterIdentityClosure(
        identityService,
        erasureId,
        accountId,
      )
      return jsonResponse({ closed: true })
    } catch {
      return jsonResponse({ code: 'identity_unavailable' }, 503)
    }
  }

  async function closeTechnicalAccountAfterIdentityClosure(
    identityService: ReturnType<typeof IdentityService>,
    erasureId: string,
    expectedAccountId?: string,
  ): Promise<AccountErasureResult> {
    const status = await identityService.getInternalAccountErasureStatus(erasureId)
    if (status.state !== 'closed') {
      throw new Error('Identity account closure could not be confirmed.')
    }
    toBrowserAccountErasureStatus(status)
    if (status.erasure === 'completed') {
      return status
    }

    let target: Awaited<
      ReturnType<typeof identityService.getInternalAccountErasureTarget>
    >
    try {
      target = await identityService.getInternalAccountErasureTarget(erasureId)
    } catch (error) {
      const latestStatus = await identityService
        .getInternalAccountErasureStatus(erasureId)
        .catch(() => null)
      if (latestStatus?.state === 'closed' && latestStatus.erasure === 'completed') {
        toBrowserAccountErasureStatus(latestStatus)
        return latestStatus
      }
      throw error
    }
    if (
      target.erasure_id !== erasureId ||
      (expectedAccountId !== undefined && target.account_id !== expectedAccountId)
    ) {
      throw new Error('Identity account closure target could not be confirmed.')
    }
    const accountId = target.account_id

    const client = await pool.connect()
    let transactionOpen = false
    let releaseError: Error | undefined
    try {
      await client.query('BEGIN')
      transactionOpen = true
      const user = await client.query<{ email: string }>(
        'SELECT email FROM better_auth_users WHERE id = $1 FOR UPDATE',
        [accountId],
      )
      const email = user.rows[0]?.email
      await client.query('DELETE FROM better_auth_sessions WHERE user_id = $1', [
        accountId,
      ])
      await client.query('DELETE FROM better_auth_accounts WHERE user_id = $1', [
        accountId,
      ])
      await client.query(
        'DELETE FROM better_auth_verifications WHERE identifier = $1 OR strpos(value, $2) > 0',
        [email ?? null, accountId],
      )
      await client.query('DELETE FROM better_auth_users WHERE id = $1', [accountId])
      await client.query('COMMIT')
      transactionOpen = false
    } catch (error) {
      if (transactionOpen) {
        try {
          await client.query('ROLLBACK')
        } catch (rollbackError) {
          releaseError =
            rollbackError instanceof Error
              ? rollbackError
              : new Error('Better Auth rollback failed.')
        }
      }
      throw error
    } finally {
      client.release(releaseError)
    }

    await identityService.acknowledgeAccountErasure(erasureId)
    const acknowledgedStatus =
      await identityService.getInternalAccountErasureStatus(erasureId)
    if (acknowledgedStatus.state !== 'closed') {
      throw new Error('Identity account erasure acknowledgement could not be confirmed.')
    }
    toBrowserAccountErasureStatus(acknowledgedStatus)
    return acknowledgedStatus
  }

  async function getAccountDeletionStatus(
    request: Request,
  ): Promise<AccountErasureResult | null> {
    const statusRequest = new Request(
      new URL('/api/auth/account/deletion', request.url),
      { method: 'GET', headers: request.headers, redirect: 'manual' },
    )
    const response = await auth.handler(statusRequest)
    if (!response.ok) return null

    const body: unknown = await response.json().catch(() => null)
    const parsed = z
      .object({
        state: z.literal('closed'),
        closedAt: z.string().datetime({ offset: true }),
        erasure: z.enum(['pending', 'completed']),
      })
      .strict()
      .safeParse(body)
    if (!parsed.success) return null
    return {
      state: 'closed',
      closed_at: parsed.data.closedAt,
      erasure: parsed.data.erasure,
    }
  }

  return {
    auth,
    handler: auth.handler,
    getCurrentAccess,
    deleteRejectedSession: deleteSession,
    publishMainPageEntered,
    issueBrowserDataCapability: handleIssueBrowserDataCapability,
    validateBrowserDataCapability: handleValidateBrowserDataCapability,
    closeTechnicalIdentity: handleCloseTechnicalIdentity,
    getAccountDeletionStatus,
    close: () => Promise.all([pool.end(), activityPool.end()]),
  }

  async function withAccountActivity<Result>(
    accountId: string,
    accessVersion: number,
    action: () => Promise<Result>,
    request?: Request,
    sessionId?: string,
  ): Promise<Result> {
    return accountActivityScope.withSharedActivity(accountId, async () => {
      try {
        await requestIdentityService(request).admitAccountActivity(
          accountId,
          accessVersion,
          sessionId,
        )
      } catch (error) {
        if (isIdentityUnauthorized(error)) {
          throw APIError.from('UNAUTHORIZED', {
            code: 'unauthorized',
            message: 'Entre novamente para continuar.',
          })
        }
        throw APIError.from('SERVICE_UNAVAILABLE', {
          code: 'identity_unavailable',
          message: 'Não foi possível validar sua conta agora. Tente novamente.',
        })
      }
      return action()
    })
  }
}

function createIdentityPlugin(
  requestIdentityService: (request?: Request) => ReturnType<typeof IdentityService>,
  getAccessToken: (headers: Headers) => Promise<string>,
  withAccountActivity: <Result>(
    accountId: string,
    accessVersion: number,
    action: () => Promise<Result>,
    request?: Request,
    sessionId?: string,
  ) => Promise<Result>,
  closeTechnicalAccountAfterIdentityClosure: (
    identityService: ReturnType<typeof IdentityService>,
    erasureId: string,
    expectedAccountId?: string,
  ) => Promise<AccountErasureResult>,
) {
  return {
    id: 'shifu-identity-sign-in',
    endpoints: {
      accountProfile: createAuthEndpoint(
        '/account',
        { method: 'GET', requireHeaders: true },
        async (context) => {
          context.setHeader('Cache-Control', 'no-store')
          const session = await requireAccountSession(context)
          try {
            const token = await getAccessToken(context.headers)
            const profile = await requestIdentityService(
              context.request,
            ).getAccountProfile(token)
            const safeProfile = toAccountProfile(profile)
            await withAccountActivity(
              session.user.id,
              session.session.accessVersion,
              () =>
                reconcileTechnicalName(
                  context,
                  session.user.id,
                  session.user.name,
                  safeProfile.displayName,
                ),
              context.request,
              session.session.id,
            )
            return context.json(safeProfile)
          } catch (error) {
            throwAccountError(error)
          }
        },
      ),
      updateAccountProfile: createAuthEndpoint(
        '/account/profile',
        {
          method: 'POST',
          requireHeaders: true,
          body: z
            .object({
              displayName: z.string(),
              timeZone: z.string(),
              appearance: z.enum(ACCOUNT_APPEARANCES),
            })
            .strict(),
        },
        async (context) => {
          context.setHeader('Cache-Control', 'no-store')
          const session = await requireAccountSession(context)
          try {
            const token = await getAccessToken(context.headers)
            const profile = await requestIdentityService(
              context.request,
            ).updateAccountProfile(token, context.body)
            const safeProfile = toAccountProfile(profile)
            await withAccountActivity(
              session.user.id,
              session.session.accessVersion,
              () =>
                reconcileTechnicalName(
                  context,
                  session.user.id,
                  session.user.name,
                  safeProfile.displayName,
                ),
              context.request,
              session.session.id,
            )
            return context.json(safeProfile)
          } catch (error) {
            throwAccountError(error)
          }
        },
      ),
      changeAccountPassword: createAuthEndpoint(
        '/account/password',
        {
          method: 'POST',
          requireHeaders: true,
          body: z
            .object({ currentPassword: z.string(), newPassword: z.string() })
            .strict(),
        },
        async (context) => {
          context.setHeader('Cache-Control', 'no-store')
          await requireAccountSession(context)
          const token = await getAccessToken(context.headers)
          try {
            const result = await requestIdentityService(
              context.request,
            ).changeAccountPassword(token, context.body)
            if (result.changed !== true)
              throw APIError.from('SERVICE_UNAVAILABLE', {
                code: 'result_uncertain',
                message: 'Não foi possível confirmar a troca.',
              })
            return context.json({ changed: true })
          } catch (error) {
            throwAccountError(error, true)
          }
        },
      ),
      prepareAccountDeletion: createAuthEndpoint(
        '/account/deletion/prepare',
        { method: 'POST', requireHeaders: true },
        async (context) => {
          context.setHeader('Cache-Control', 'no-store')
          requireSameOriginRequest(context.request)
          const session = await requireActiveIdentitySession(
            context,
            getAccessToken,
            requestIdentityService,
          )
          const now = Date.now()
          const erasureCookie: AccountErasureCookie = {
            erasureId: randomUUID(),
            actorBinding: createActorBinding(context.context.secret, session.user.id),
            firstConfirmationExpiresAt:
              now + ACCOUNT_ERASURE_FIRST_CONFIRMATION_LIFETIME_MS,
            expiresAt: now + ACCOUNT_ERASURE_COOKIE_LIFETIME_SECONDS * 1000,
          }
          await context.setSignedCookie(
            ACCOUNT_ERASURE_COOKIE_NAME,
            JSON.stringify(erasureCookie),
            context.context.secret,
            {
              httpOnly: true,
              maxAge: ACCOUNT_ERASURE_COOKIE_LIFETIME_SECONDS,
              path: '/',
              sameSite: 'strict',
              secure: true,
            },
          )
          return context.json({ state: 'prepared' as const })
        },
      ),
      deleteAccount: createAuthEndpoint(
        '/account/deletion',
        {
          method: 'POST',
          requireHeaders: true,
          body: accountDeletionBody,
        },
        async (context) => {
          context.setHeader('Cache-Control', 'no-store')
          requireSameOriginRequest(context.request)
          const session = await requireAccountSession(context)
          const erasureCookie = await getAccountErasureCookie(context)
          if (
            !erasureCookie ||
            erasureCookie.expiresAt <= Date.now() ||
            !isActorBindingValid(
              erasureCookie.actorBinding,
              context.context.secret,
              session.user.id,
            )
          ) {
            throw accountDeletionPreparationError()
          }

          const identityService = requestIdentityService(context.request)
          if (erasureCookie.firstConfirmationExpiresAt <= Date.now()) {
            let status: AccountErasureResult
            try {
              status = await identityService.getInternalAccountErasureStatus(
                erasureCookie.erasureId,
              )
            } catch {
              throw accountDeletionPreparationError()
            }
            toBrowserAccountErasureStatus(status)
            try {
              const recoveredStatus = await closeTechnicalAccountAfterIdentityClosure(
                identityService,
                erasureCookie.erasureId,
                session.user.id,
              )
              deleteSessionCookie(context)
              return context.json(toBrowserAccountErasureStatus(recoveredStatus))
            } catch (error) {
              throwAccountError(error)
            }
          }

          const accessToken = await getAccessToken(context.headers)
          try {
            const identitySession = await identityService.getCurrentSession(accessToken)
            if (identitySession.account_id !== session.user.id) {
              throw APIError.from('UNAUTHORIZED', {
                code: 'unauthorized',
                message: 'Entre novamente para continuar.',
              })
            }
            const result = await identityService.deleteAccount(accessToken, {
              erasureId: erasureCookie.erasureId,
              currentPassword: context.body.currentPassword,
              confirmed: true,
            })
            toBrowserAccountErasureStatus(result)
            const recoveredStatus = await closeTechnicalAccountAfterIdentityClosure(
              identityService,
              erasureCookie.erasureId,
              session.user.id,
            )
            deleteSessionCookie(context)
            return context.json(toBrowserAccountErasureStatus(recoveredStatus))
          } catch (error) {
            if (isIdentityUnauthorized(error)) {
              let status: AccountErasureResult | undefined
              try {
                status = await identityService.getInternalAccountErasureStatus(
                  erasureCookie.erasureId,
                )
              } catch {
                // A recovery lookup that cannot prove closure stays generic.
              }
              if (status) {
                toBrowserAccountErasureStatus(status)
                try {
                  const recoveredStatus = await closeTechnicalAccountAfterIdentityClosure(
                    identityService,
                    erasureCookie.erasureId,
                    session.user.id,
                  )
                  deleteSessionCookie(context)
                  return context.json(toBrowserAccountErasureStatus(recoveredStatus))
                } catch (cleanupError) {
                  throwAccountError(cleanupError)
                }
              }
            }
            throwAccountError(error)
          }
        },
      ),
      getAccountDeletionStatus: createAuthEndpoint(
        '/account/deletion',
        { method: 'GET' },
        async (context) => {
          context.setHeader('Cache-Control', 'no-store')
          const erasureCookie = await getAccountErasureCookie(context)
          if (!erasureCookie || erasureCookie.expiresAt <= Date.now()) {
            throw accountDeletionPreparationError()
          }

          try {
            const status = await closeTechnicalAccountAfterIdentityClosure(
              requestIdentityService(context.request),
              erasureCookie.erasureId,
            )
            return context.json(toBrowserAccountErasureStatus(status))
          } catch (error) {
            throwAccountError(error)
          }
        },
      ),
      requestPasswordRecovery: createAuthEndpoint(
        '/password-recovery',
        { method: 'POST', body: passwordRecoveryBody },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          let result: Awaited<ReturnType<typeof identityService.requestPasswordRecovery>>
          try {
            result = await identityService.requestPasswordRecovery(context.body.email)
          } catch {
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'identity_unavailable',
              message: 'Não foi possível solicitar a recuperação agora. Tente novamente.',
            })
          }

          try {
            await createPasswordRecoveryContext(
              context,
              result.recovery_handle,
              result.is_decoy,
            )
          } catch {
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'auth_persistence_unavailable',
              message: 'Não foi possível solicitar a recuperação agora. Tente novamente.',
            })
          }

          return context.json({ accepted: true })
        },
      ),
      getPasswordRecoveryStatus: createAuthEndpoint(
        '/password-recovery/status',
        { method: 'GET' },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          const recoveryContext = await getPasswordRecoveryContext(context)
          if (!recoveryContext) {
            return context.json({ state: 'delivery_issue', retryAfterSeconds: null })
          }
          if (recoveryContext.isDecoy) {
            const retryAfterSeconds = getPasswordRecoveryCooldownSeconds(
              recoveryContext.expiresAt,
            )
            return context.json({
              state: retryAfterSeconds === null ? 'ready' : 'cooldown',
              retryAfterSeconds,
            })
          }

          try {
            const status = await identityService.getPasswordRecoveryStatus(
              recoveryContext.handle,
            )
            return context.json({
              state: status.state,
              retryAfterSeconds: status.retry_after_seconds,
            })
          } catch {
            return context.json({
              state: 'delivery_issue',
              retryAfterSeconds: null,
            })
          }
        },
      ),
      retryPasswordRecovery: createAuthEndpoint(
        '/password-recovery/retry',
        { method: 'POST' },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          const recoveryContext = await getPasswordRecoveryContext(context)
          if (!recoveryContext) {
            return context.json({ state: 'delivery_issue', retryAfterSeconds: null })
          }
          if (recoveryContext.isDecoy) {
            return context.json({ state: 'cooldown', retryAfterSeconds: 60 })
          }

          try {
            const result = await identityService.retryPasswordRecovery(
              recoveryContext.handle,
            )
            await replacePasswordRecoveryContext(
              context,
              result.recovery_handle,
              result.is_decoy,
            )
            return context.json({
              state: result.is_decoy ? 'cooldown' : 'ready',
              retryAfterSeconds: result.is_decoy ? 60 : null,
            })
          } catch {
            return context.json({ state: 'delivery_issue', retryAfterSeconds: null })
          }
        },
      ),
      getPasswordResetLinkStatus: createAuthEndpoint(
        '/password-reset-link/status',
        { method: 'POST', body: passwordResetLinkBody },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          if (!isRecoveryToken(context.body.token)) {
            return context.json({ result: 'invalid' })
          }

          try {
            const result = await identityService.getPasswordResetLinkStatus(
              context.body.token,
            )
            return context.json({ result: result.result })
          } catch {
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'identity_unavailable',
              message: 'Não foi possível verificar este link agora. Tente novamente.',
            })
          }
        },
      ),
      resetPassword: createAuthEndpoint(
        '/password-reset',
        { method: 'POST', body: passwordResetBody },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          if (!isRecoveryToken(context.body.token)) {
            return context.json({ result: 'invalid', redirectTo: ROUTES.login })
          }

          let result: Awaited<ReturnType<typeof identityService.resetPassword>>
          try {
            result = await identityService.resetPassword(
              context.body.token,
              context.body.password,
              context.body.passwordConfirmation,
            )
          } catch {
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'identity_unavailable',
              message: 'Não foi possível redefinir sua senha agora. Tente novamente.',
            })
          }

          if (result.result !== 'reset') {
            return context.json({ result: result.result, redirectTo: ROUTES.login })
          }

          try {
            await context.context.internalAdapter.deleteUserSessions(result.account_id)
          } catch {
            telemetry.emit({
              level: 'WARNING',
              event: 'dependency.unavailable',
              operation: 'dependency.check',
              dependency: 'better-auth',
              result: 'unavailable',
            })
          }

          try {
            await clearPasswordRecoveryContext(context)
          } catch {
            telemetry.emit({
              level: 'WARNING',
              event: 'dependency.unavailable',
              operation: 'dependency.check',
              dependency: 'better-auth',
              result: 'unavailable',
            })
          }
          deleteSessionCookie(context)

          return context.json({
            result: 'reset',
            redirectTo: ROUTES.login,
            requiresEmailConfirmation: result.requires_email_confirmation,
          })
        },
      ),
      registerIdentity: createAuthEndpoint(
        '/register/identity',
        { method: 'POST', body: registerBody },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          let registration: Awaited<ReturnType<typeof identityService.registerAccount>>
          try {
            registration = await identityService.registerAccount(context.body)
          } catch {
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'identity_unavailable',
              message: 'Não foi possível criar sua conta agora. Tente novamente.',
            })
          }

          try {
            await createPendingContext(
              context,
              registration.pending_handle,
              undefined,
              registration.is_decoy,
            )
            return context.json({ redirectTo: ROUTES.pendingConfirmation })
          } catch {
            try {
              await createRecoverablePendingContext(
                context,
                registration.pending_handle,
                registration.is_decoy,
              )
              return context.json({ redirectTo: ROUTES.pendingConfirmation })
            } catch {
              throw APIError.from('SERVICE_UNAVAILABLE', {
                code: 'auth_persistence_unavailable',
                message: 'Não foi possível criar sua conta agora. Tente novamente.',
              })
            }
          }
        },
      ),
      pendingConfirmation: createAuthEndpoint(
        '/pending-confirmation',
        { method: 'GET' },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          const pendingContext = await getPendingContext(context)
          if (!pendingContext) {
            return context.json({ state: 'delivery_issue', retryAfterSeconds: null })
          }
          if (pendingContext.isDecoy) {
            return context.json({ state: 'cooldown', retryAfterSeconds: 60 })
          }

          try {
            const status = await identityService.getPendingConfirmationStatus(
              pendingContext.handle,
            )
            return context.json({
              state: status.state,
              retryAfterSeconds: status.retry_after_seconds,
            })
          } catch {
            return context.json({ state: 'delivery_issue', retryAfterSeconds: null })
          }
        },
      ),
      resendPendingConfirmation: createAuthEndpoint(
        '/pending-confirmation/resend',
        { method: 'POST' },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          const pendingContext = await getPendingContext(context)
          if (!pendingContext) {
            return context.json({ result: 'accepted', retryAfterSeconds: null })
          }
          if (pendingContext.isDecoy) {
            return context.json({ result: 'cooldown', retryAfterSeconds: 60 })
          }

          try {
            const result = await identityService.resendConfirmation(pendingContext.handle)
            return context.json({
              result: result.result,
              retryAfterSeconds: result.retry_after_seconds,
            })
          } catch {
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'identity_unavailable',
              message: 'Não foi possível reenviar agora. Tente novamente.',
            })
          }
        },
      ),
      confirmEmail: createAuthEndpoint(
        '/confirm-email',
        { method: 'POST', body: confirmEmailBody },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          let result: Awaited<ReturnType<typeof identityService.confirmEmail>>
          try {
            result = await identityService.confirmEmail(context.body.token)
          } catch {
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'identity_unavailable',
              message: 'Não foi possível confirmar agora. Tente novamente.',
            })
          }

          if (result.result !== 'activated') {
            return context.json({ result: result.result, redirectTo: ROUTES.login })
          }

          const pendingContext = await getPendingContext(context)
          const hasMatchingPendingContext =
            pendingContext !== null &&
            (await identityService.verifyPendingConfirmationContext(
              pendingContext.handle,
              result.profile.account_id,
            ))
          if (!hasMatchingPendingContext) {
            await clearPendingContext(context)
            return context.json({ result: 'activated', redirectTo: ROUTES.login })
          }

          try {
            await withAccountActivity(
              result.profile.account_id,
              result.access_version,
              async () => {
                const internalAdapter = context.context.internalAdapter
                let sessionToken: string | undefined
                let createdUserId: string | undefined
                try {
                  const technicalUser = await upsertTechnicalUser(context, result)
                  createdUserId = technicalUser.created
                    ? technicalUser.user.id
                    : undefined
                  const session = await internalAdapter.createSession(
                    technicalUser.user.id,
                    false,
                    { accessVersion: result.access_version },
                  )
                  sessionToken = session.token
                  await clearPendingContext(context)
                  await setSessionCookie(context, { session, user: technicalUser.user })
                } catch (error) {
                  await Promise.allSettled([
                    sessionToken
                      ? internalAdapter.deleteSession(sessionToken)
                      : Promise.resolve(),
                    createdUserId
                      ? internalAdapter.deleteUser(createdUserId)
                      : Promise.resolve(),
                  ])
                  deleteSessionCookie(context)
                  throw error
                }
              },
              context.request,
            )
          } catch (error) {
            if (error instanceof APIError && error.status === 'UNAUTHORIZED') throw error
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'auth_persistence_unavailable',
              message: 'Não foi possível confirmar agora. Tente novamente.',
            })
          }

          return context.json({ result: 'activated', redirectTo: ROUTES.root })
        },
      ),
      signInIdentity: createAuthEndpoint(
        '/sign-in/identity',
        {
          method: 'POST',
          body: signInBody,
        },
        async (context) => {
          const identityService = requestIdentityService(context.request)
          let authentication: Awaited<
            ReturnType<typeof identityService.validateCredentials>
          >
          try {
            authentication = await identityService.validateCredentials(
              context.body.email,
              context.body.password,
            )
          } catch (error) {
            if (
              (error instanceof AuthError && error.kind === 'authentication-rejected') ||
              (error instanceof RestError && error.statusCode === 401)
            ) {
              throw APIError.from('UNAUTHORIZED', {
                code: 'invalid_credentials',
                message: 'E-mail ou senha inválidos.',
              })
            }

            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'identity_unavailable',
              message: 'Não foi possível entrar agora. Tente novamente.',
            })
          }

          if (authentication.access === 'activation-only') {
            if (!isPendingHandle(authentication.pending_handle)) {
              throw APIError.from('SERVICE_UNAVAILABLE', {
                code: 'identity_unavailable',
                message: 'Não foi possível entrar agora. Tente novamente.',
              })
            }
            await createPendingContext(
              context,
              authentication.pending_handle,
              authentication.profile.account_id,
            )

            return context.json({
              access: authentication.access,
              redirectTo: ROUTES.pendingConfirmation,
            })
          }

          try {
            await withAccountActivity(
              authentication.profile.account_id,
              authentication.access_version,
              async () => {
                const internalAdapter = context.context.internalAdapter
                let sessionToken: string | undefined
                let createdUserId: string | undefined
                try {
                  const technicalUser = await upsertTechnicalUser(context, authentication)
                  createdUserId = technicalUser.created
                    ? technicalUser.user.id
                    : undefined
                  const session = await internalAdapter.createSession(
                    technicalUser.user.id,
                    false,
                    { accessVersion: authentication.access_version },
                  )
                  sessionToken = session.token
                  await clearPendingCookie(context)
                  await setSessionCookie(context, { session, user: technicalUser.user })
                } catch (error) {
                  await Promise.allSettled([
                    sessionToken
                      ? internalAdapter.deleteSession(sessionToken)
                      : Promise.resolve(),
                    createdUserId
                      ? internalAdapter.deleteUser(createdUserId)
                      : Promise.resolve(),
                  ])
                  deleteSessionCookie(context)
                  throw error
                }
              },
              context.request,
            )
          } catch (error) {
            if (error instanceof APIError && error.status === 'UNAUTHORIZED') throw error
            deleteSessionCookie(context)
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'auth_persistence_unavailable',
              message: 'Não foi possível entrar agora. Tente novamente.',
            })
          }

          return context.json({
            access: authentication.access,
            redirectTo: ROUTES.root,
          })
        },
      ),
      pendingSignOut: createAuthEndpoint(
        '/pending-confirmation/sign-out',
        {
          method: 'POST',
          requireHeaders: true,
        },
        async (context) => {
          try {
            await clearPendingContext(context)
          } catch {
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'pending_persistence_unavailable',
              message: 'Não foi possível sair agora. Tente novamente.',
            })
          }

          return context.json({})
        },
      ),
    },
  } satisfies BetterAuthPlugin
}

async function clearPendingCookie(context: GenericEndpointContext) {
  await context.setSignedCookie(PENDING_COOKIE_NAME, '', context.context.secret, {
    httpOnly: true,
    maxAge: 0,
    path: '/',
    sameSite: 'lax',
    secure: context.context.options.advanced?.useSecureCookies ?? false,
  })
}

async function clearPasswordRecoveryCookie(context: GenericEndpointContext) {
  await context.setSignedCookie(
    PASSWORD_RECOVERY_COOKIE_NAME,
    '',
    context.context.secret,
    {
      httpOnly: true,
      maxAge: 0,
      path: '/',
      sameSite: 'lax',
      secure: context.context.options.advanced?.useSecureCookies ?? false,
    },
  )
}

async function createPendingContext(
  context: GenericEndpointContext,
  pendingHandle: string,
  accountId?: string,
  isDecoy = false,
) {
  const identifier = crypto.randomUUID()
  await context.context.internalAdapter.createVerificationValue({
    identifier,
    value: JSON.stringify({ pendingHandle, accountId, isDecoy }),
    expiresAt: new Date(Date.now() + PENDING_FLOW_LIFETIME_MS),
  })
  await context.setSignedCookie(PENDING_COOKIE_NAME, identifier, context.context.secret, {
    httpOnly: true,
    maxAge: PENDING_FLOW_LIFETIME_SECONDS,
    path: '/',
    sameSite: 'lax',
    secure: context.context.options.advanced?.useSecureCookies ?? false,
  })
}

async function createRecoverablePendingContext(
  context: GenericEndpointContext,
  pendingHandle: string,
  isDecoy: boolean,
) {
  await context.setSignedCookie(
    PENDING_COOKIE_NAME,
    JSON.stringify({ pendingHandle, isDecoy }),
    context.context.secret,
    {
      httpOnly: true,
      maxAge: PENDING_FLOW_LIFETIME_SECONDS,
      path: '/',
      sameSite: 'lax',
      secure: context.context.options.advanced?.useSecureCookies ?? false,
    },
  )
}

async function createPasswordRecoveryContext(
  context: GenericEndpointContext,
  recoveryHandle: string,
  isDecoy: boolean,
) {
  const identifier = crypto.randomUUID()
  await context.context.internalAdapter.createVerificationValue({
    identifier,
    value: JSON.stringify({ isDecoy, recoveryHandle }),
    expiresAt: new Date(Date.now() + PASSWORD_RECOVERY_LIFETIME_MS),
  })
  await context.setSignedCookie(
    PASSWORD_RECOVERY_COOKIE_NAME,
    identifier,
    context.context.secret,
    {
      httpOnly: true,
      maxAge: PASSWORD_RECOVERY_LIFETIME_SECONDS,
      path: '/',
      sameSite: 'lax',
      secure: context.context.options.advanced?.useSecureCookies ?? false,
    },
  )
}

async function replacePasswordRecoveryContext(
  context: GenericEndpointContext,
  recoveryHandle: string,
  isDecoy: boolean,
) {
  const identifier = await context.getSignedCookie(
    PASSWORD_RECOVERY_COOKIE_NAME,
    context.context.secret,
  )
  if (identifier) {
    await context.context.internalAdapter.deleteVerificationByIdentifier(identifier)
  }
  await createPasswordRecoveryContext(context, recoveryHandle, isDecoy)
}

async function getPendingContext(
  context: GenericEndpointContext,
): Promise<{ handle: string; isDecoy: boolean } | null> {
  const identifier = await context.getSignedCookie(
    PENDING_COOKIE_NAME,
    context.context.secret,
  )
  if (!identifier) return null

  const verification =
    await context.context.internalAdapter.findVerificationValue(identifier)
  if (verification && verification.expiresAt <= new Date()) return null

  try {
    const value: unknown = JSON.parse(verification?.value ?? identifier)
    if (
      !isRecord(value) ||
      typeof value.pendingHandle !== 'string' ||
      !isPendingHandle(value.pendingHandle)
    ) {
      return null
    }
    return { handle: value.pendingHandle, isDecoy: value.isDecoy === true }
  } catch {
    return null
  }
}

async function clearPendingContext(context: GenericEndpointContext) {
  const identifier = await context.getSignedCookie(
    PENDING_COOKIE_NAME,
    context.context.secret,
  )
  if (identifier) {
    await context.context.internalAdapter.deleteVerificationByIdentifier(identifier)
  }
  await clearPendingCookie(context)
}

async function getPasswordRecoveryContext(
  context: GenericEndpointContext,
): Promise<{ expiresAt: Date; handle: string; isDecoy: boolean } | null> {
  const identifier = await context.getSignedCookie(
    PASSWORD_RECOVERY_COOKIE_NAME,
    context.context.secret,
  )
  if (!identifier) return null

  const verification =
    await context.context.internalAdapter.findVerificationValue(identifier)
  if (!verification || verification.expiresAt <= new Date()) return null

  try {
    const value: unknown = JSON.parse(verification.value)
    if (
      !isRecord(value) ||
      typeof value.recoveryHandle !== 'string' ||
      !isPendingHandle(value.recoveryHandle)
    ) {
      return null
    }
    return {
      expiresAt: verification.expiresAt,
      handle: value.recoveryHandle,
      isDecoy: value.isDecoy === true,
    }
  } catch {
    return null
  }
}

function getPasswordRecoveryCooldownSeconds(expiresAt: Date): number | null {
  const cooldownEndsAt =
    expiresAt.getTime() - PASSWORD_RECOVERY_LIFETIME_MS + PASSWORD_RECOVERY_COOLDOWN_MS
  const remainingMilliseconds = cooldownEndsAt - Date.now()
  if (remainingMilliseconds <= 0) return null
  return Math.max(1, Math.ceil(remainingMilliseconds / 1000))
}

async function clearPasswordRecoveryContext(context: GenericEndpointContext) {
  const identifier = await context.getSignedCookie(
    PASSWORD_RECOVERY_COOKIE_NAME,
    context.context.secret,
  )
  if (identifier) {
    await context.context.internalAdapter.deleteVerificationByIdentifier(identifier)
  }
  await clearPasswordRecoveryCookie(context)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isPendingHandle(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value)
}

function isRecoveryToken(value: unknown): value is string {
  return isPendingHandle(value)
}

async function upsertTechnicalUser(
  context: GenericEndpointContext,
  authentication:
    | Awaited<ReturnType<IdentityService['validateCredentials']>>
    | Extract<
        Awaited<ReturnType<IdentityService['confirmEmail']>>,
        { result: 'activated' }
      >,
) {
  const profile = authentication.profile
  const existingUser = await context.context.internalAdapter.findUserById(
    profile.account_id,
  )
  const userData = {
    id: profile.account_id,
    name: profile.display_name,
    email: profile.email,
    emailVerified: true,
    image: null,
  }

  if (existingUser) {
    return {
      user: await context.context.internalAdapter.updateUser(
        profile.account_id,
        userData,
      ),
      created: false,
    }
  }

  return {
    user: await context.context.internalAdapter.createUser(userData),
    created: true,
  }
}

let provider: ReturnType<typeof BetterAuthProvider> | undefined

export const getBetterAuthProvider = () => {
  provider ??= BetterAuthProvider()
  return provider
}

async function requireActiveIdentitySession(
  context: GenericEndpointContext,
  getAccessToken: (headers: Headers) => Promise<string>,
  requestIdentityService: (request?: Request) => ReturnType<typeof IdentityService>,
) {
  const session = await requireAccountSession(context)
  try {
    if (!context.headers) {
      throw APIError.from('UNAUTHORIZED', {
        code: 'unauthorized',
        message: 'Entre novamente para continuar.',
      })
    }
    const accessToken = await getAccessToken(context.headers)
    const identitySession = await requestIdentityService(
      context.request,
    ).getCurrentSession(accessToken)
    if (identitySession.account_id !== session.user.id) {
      throw APIError.from('UNAUTHORIZED', {
        code: 'unauthorized',
        message: 'Entre novamente para continuar.',
      })
    }
    return session
  } catch (error) {
    if (error instanceof APIError) throw error
    throw APIError.from('SERVICE_UNAVAILABLE', {
      code: 'identity_unavailable',
      message: 'Não foi possível validar sua conta agora. Tente novamente.',
    })
  }
}

async function getAccountErasureCookie(
  context: GenericEndpointContext,
): Promise<AccountErasureCookie | null> {
  const value = await context.getSignedCookie(
    ACCOUNT_ERASURE_COOKIE_NAME,
    context.context.secret,
  )
  if (!value) return null

  try {
    const parsed = z
      .object({
        erasureId: z.string().uuid(),
        actorBinding: z.string().regex(/^[A-Za-z0-9_-]{43}$/),
        firstConfirmationExpiresAt: z.number().int().positive(),
        expiresAt: z.number().int().positive(),
      })
      .strict()
      .parse(JSON.parse(value))
    return parsed.expiresAt > Date.now() ? parsed : null
  } catch {
    return null
  }
}

function createActorBinding(secret: string, actorId: string): string {
  return createHmac('sha256', secret)
    .update(`shifu:account-erasure:actor:${actorId}`, 'utf8')
    .digest('base64url')
}

function isActorBindingValid(
  actorBinding: string,
  secret: string,
  actorId: string,
): boolean {
  const expected = Buffer.from(createActorBinding(secret, actorId), 'base64url')
  const actual = Buffer.from(actorBinding, 'base64url')
  return actual.length === expected.length && timingSafeEqual(actual, expected)
}

function toBrowserAccountErasureStatus(result: AccountErasureResult) {
  const parsed = z
    .object({
      state: z.literal('closed'),
      closed_at: z.string().datetime({ offset: true }),
      erasure: z.enum(['pending', 'completed']),
    })
    .strict()
    .safeParse(result)
  if (!parsed.success) {
    throw APIError.from('SERVICE_UNAVAILABLE', {
      code: 'invalid_response',
      message: 'Não foi possível confirmar o estado da exclusão agora.',
    })
  }
  return {
    state: parsed.data.state,
    closedAt: parsed.data.closed_at,
    erasure: parsed.data.erasure,
  }
}

function accountDeletionPreparationError() {
  return APIError.from('FORBIDDEN', {
    code: 'preparation_expired',
    message: 'Não foi possível confirmar essa solicitação. Inicie novamente.',
  })
}

function isIdentityUnauthorized(error: unknown): boolean {
  return (
    (error instanceof AuthError && error.kind === 'authentication-rejected') ||
    (error instanceof RestError && error.statusCode === HTTP_STATUS_CODE.unauthorized)
  )
}

function requireSameOriginRequest(request: Request | undefined): void {
  if (!request || !isSameOriginRequest(request)) {
    throw APIError.from('FORBIDDEN', {
      code: 'invalid_origin',
      message: 'Não foi possível processar essa solicitação.',
    })
  }
}

function isSameOriginRequest(request: Request): boolean {
  const origin = request.headers.get('Origin')
  if (!origin) return false
  try {
    return new URL(origin).origin === new URL(request.url).origin
  } catch {
    return false
  }
}

function isSecureRequest(request: Request, baseURL: string): boolean {
  const requestUrl = new URL(request.url)
  if (requestUrl.protocol === 'https:') return true
  if (new URL(baseURL).protocol === 'https:') return false
  return ['localhost', '127.0.0.1', '[::1]', '::1'].includes(requestUrl.hostname)
}

function isValidBrowserCapability(value: string): boolean {
  return /^[A-Za-z0-9_-]{32,256}$/.test(value)
}

function isSecretMatch(actual: string | null, expected: string): boolean {
  if (!actual) return false
  const actualBytes = Buffer.from(actual, 'utf8')
  const expectedBytes = Buffer.from(expected, 'utf8')
  return (
    actualBytes.length === expectedBytes.length &&
    timingSafeEqual(actualBytes, expectedBytes)
  )
}

function jsonResponse(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Cache-Control': 'no-store',
      'Content-Type': 'application/json; charset=utf-8',
    },
  })
}

async function requireAccountSession(context: GenericEndpointContext) {
  const session = await getSessionFromCtx(context, { disableRefresh: true })
  if (!session)
    throw APIError.from('UNAUTHORIZED', {
      code: 'unauthorized',
      message: 'Entre novamente para continuar.',
    })
  return session
}

async function reconcileTechnicalName(
  context: GenericEndpointContext,
  accountId: string,
  technicalName: string,
  canonicalName: string,
) {
  if (technicalName === canonicalName) return
  try {
    await context.context.internalAdapter.updateUser(accountId, { name: canonicalName })
  } catch {
    telemetry.emit({
      level: 'WARNING',
      event: 'dependency.unavailable',
      operation: 'dependency.check',
      dependency: 'better-auth',
      result: 'unavailable',
    })
  }
}

function toAccountProfile(
  profile: Awaited<ReturnType<IdentityService['getAccountProfile']>>,
) {
  const parsed = z
    .object({
      account_id: z.string().min(1),
      display_name: z.string().min(1),
      email: z.string().min(1),
      time_zone: z.string().nullable(),
      appearance: z.enum(ACCOUNT_APPEARANCES),
    })
    .safeParse(profile)
  if (!parsed.success)
    throw APIError.from('SERVICE_UNAVAILABLE', {
      code: 'invalid_response',
      message: 'Não foi possível carregar a conta.',
    })
  return {
    accountId: parsed.data.account_id,
    displayName: parsed.data.display_name,
    email: parsed.data.email,
    timeZone: parsed.data.time_zone,
    appearance: parsed.data.appearance,
  }
}

function throwAccountError(error: unknown, passwordChange = false): never {
  if (error instanceof APIError) throw error
  if (error instanceof RestError) {
    if (error.statusCode === HTTP_STATUS_CODE.unauthorized)
      throw APIError.from('UNAUTHORIZED', {
        code: 'unauthorized',
        message: 'Entre novamente para continuar.',
      })
    if (
      error.statusCode === HTTP_STATUS_CODE.forbidden &&
      error.code === 'invalid_current_password'
    )
      throw APIError.from('FORBIDDEN', {
        code: error.code,
        message: 'A senha atual está incorreta.',
      })
    if (
      error.statusCode === HTTP_STATUS_CODE.badRequest &&
      [
        'invalid_display_name',
        'invalid_time_zone',
        'invalid_appearance',
        'invalid_new_password',
      ].includes(error.code ?? '')
    )
      throw APIError.from('BAD_REQUEST', {
        code: error.code ?? 'invalid_input',
        message: 'Confira o campo informado.',
      })
    if (error.statusCode > 0)
      throw APIError.from('SERVICE_UNAVAILABLE', {
        code: 'identity_unavailable',
        message: 'Não foi possível concluir agora. Tente novamente.',
      })
  }
  throw APIError.from('SERVICE_UNAVAILABLE', {
    code: passwordChange ? 'result_uncertain' : 'identity_unavailable',
    message: passwordChange
      ? 'Não foi possível confirmar a troca.'
      : 'Não foi possível carregar a conta.',
  })
}
