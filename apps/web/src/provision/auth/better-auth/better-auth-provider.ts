import {
  betterAuth,
  type BetterAuthPlugin,
  type GenericEndpointContext,
} from 'better-auth'
import { APIError, createAuthEndpoint } from 'better-auth/api'
import { deleteSessionCookie, setSessionCookie } from 'better-auth/cookies'
import { jwt } from 'better-auth/plugins'
import { Pool, types as pgTypes } from 'pg'
import { z } from 'zod'

import { ROUTES } from '@/constants/routes'
import { AuthError } from '@/core/errors/auth-error'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { IdentityService } from '@/rest/services/identity-service'

import { BETTER_AUTH_OPTIONS, BetterAuthConfig } from './better-auth-config'

const PENDING_COOKIE_NAME = 'shifu-pending-flow'
const PENDING_FLOW_LIFETIME_SECONDS = 15 * 60
const PENDING_FLOW_LIFETIME_MS = PENDING_FLOW_LIFETIME_SECONDS * 1000

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

type AuthenticatedAccess = {
  accountId: string
  displayName: string
  timeZone: string | null
  accessToken: string
}

const BetterAuthProvider = () => {
  const config = BetterAuthConfig()
  pgTypes.setTypeParser(20, (value) => Number.parseInt(value, 10))
  const pool = new Pool({ connectionString: config.databaseURL })
  const identityService = IdentityService(
    AxiosRestClient(config.identityURL, {
      defaultHeaders: { 'X-Shifu-Bff-Secret': config.bffSharedSecret },
      withCredentials: false,
    }),
  )

  const identityPlugin = createIdentityPlugin(identityService)
  const auth = betterAuth({
    appName: 'Shifu',
    baseURL: config.baseURL,
    basePath: '/api/auth',
    secret: config.secret,
    database: pool,
    emailAndPassword: { enabled: false },
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

  async function getCurrentAccess(request: Request): Promise<AuthenticatedAccess | null> {
    const session = await auth.api.getSession({ headers: request.headers })
    if (!session) return null

    try {
      const token = await auth.api.getToken({ headers: request.headers })
      const accessToken = token?.token
      if (!accessToken) throw new AuthError('invalid-response', 'Token ausente.')

      const currentSession = await identityService.getCurrentSession(accessToken)
      return {
        accountId: currentSession.account_id,
        displayName: currentSession.display_name,
        timeZone: currentSession.time_zone,
        accessToken,
      }
    } catch (error) {
      await deleteSession(request)
      if (error instanceof AuthError && error.kind === 'unavailable') throw error
      return null
    }
  }

  async function deleteSession(request: Request) {
    const session = await auth.api.getSession({ headers: request.headers })
    if (!session) return

    const context = await auth.$context
    await context.internalAdapter.deleteSession(session.session.token)
  }

  async function publishMainPageEntered(access: AuthenticatedAccess) {
    try {
      await identityService.publishMainPageEntered(access.accessToken)
    } catch {
      // Observability is best effort. The access decision has already
      // completed and must not block a valid dashboard navigation.
      console.warn('Main-page entry observability is unavailable.')
    }
  }

  return {
    auth,
    handler: auth.handler,
    getCurrentAccess,
    deleteRejectedSession: deleteSession,
    publishMainPageEntered,
    close: () => pool.end(),
  }
}

function createIdentityPlugin(identityService: ReturnType<typeof IdentityService>) {
  return {
    id: 'shifu-identity-sign-in',
    endpoints: {
      registerIdentity: createAuthEndpoint(
        '/register/identity',
        { method: 'POST', body: registerBody },
        async (context) => {
          try {
            const registration = await identityService.registerAccount(context.body)
            await createPendingContext(context, registration.pending_handle)
            return context.json({ redirectTo: ROUTES.pendingConfirmation })
          } catch {
            throw APIError.from('SERVICE_UNAVAILABLE', {
              code: 'identity_unavailable',
              message: 'Não foi possível criar sua conta agora. Tente novamente.',
            })
          }
        },
      ),
      pendingConfirmation: createAuthEndpoint(
        '/pending-confirmation',
        { method: 'GET' },
        async (context) => {
          const pendingHandle = await getPendingHandle(context)
          if (!pendingHandle) {
            return context.json({ state: 'delivery_issue', retryAfterSeconds: null })
          }

          try {
            const status =
              await identityService.getPendingConfirmationStatus(pendingHandle)
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
          const pendingHandle = await getPendingHandle(context)
          if (!pendingHandle) {
            return context.json({ result: 'accepted', retryAfterSeconds: null })
          }

          try {
            const result = await identityService.resendConfirmation(pendingHandle)
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

          try {
            const technicalUser = await upsertTechnicalUser(context, result)
            const session = await context.context.internalAdapter.createSession(
              technicalUser.user.id,
              false,
              { accessVersion: result.access_version },
            )
            await clearPendingContext(context)
            await setSessionCookie(context, { session, user: technicalUser.user })
          } catch {
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
          let authentication: Awaited<
            ReturnType<typeof identityService.validateCredentials>
          >
          try {
            authentication = await identityService.validateCredentials(
              context.body.email,
              context.body.password,
            )
          } catch (error) {
            if (error instanceof AuthError && error.kind === 'authentication-rejected') {
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
            const identifier = crypto.randomUUID()
            await context.context.internalAdapter.createVerificationValue({
              identifier,
              value: JSON.stringify({
                accountId: authentication.profile.account_id,
                email: authentication.profile.email,
              }),
              expiresAt: new Date(Date.now() + PENDING_FLOW_LIFETIME_MS),
            })
            await context.setSignedCookie(
              PENDING_COOKIE_NAME,
              identifier,
              context.context.secret,
              {
                httpOnly: true,
                maxAge: PENDING_FLOW_LIFETIME_SECONDS,
                path: '/',
                sameSite: 'lax',
                secure: context.context.options.advanced?.useSecureCookies ?? false,
              },
            )

            return context.json({
              access: authentication.access,
              redirectTo: ROUTES.pendingConfirmation,
            })
          }

          let sessionToken: string | undefined
          let createdUserId: string | undefined
          try {
            const technicalUser = await upsertTechnicalUser(context, authentication)
            createdUserId = technicalUser.created ? technicalUser.user.id : undefined
            const session = await context.context.internalAdapter.createSession(
              technicalUser.user.id,
              false,
              { accessVersion: authentication.access_version },
            )
            sessionToken = session.token
            await clearPendingCookie(context)
            await setSessionCookie(context, { session, user: technicalUser.user })
          } catch {
            const internalAdapter = context.context.internalAdapter
            await Promise.allSettled([
              sessionToken
                ? internalAdapter.deleteSession(sessionToken)
                : Promise.resolve(),
              createdUserId
                ? internalAdapter.deleteUser(createdUserId)
                : Promise.resolve(),
            ])
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

async function createPendingContext(
  context: GenericEndpointContext,
  pendingHandle: string,
) {
  const identifier = crypto.randomUUID()
  await context.context.internalAdapter.createVerificationValue({
    identifier,
    value: JSON.stringify({ pendingHandle }),
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

async function getPendingHandle(context: GenericEndpointContext): Promise<string | null> {
  const identifier = await context.getSignedCookie(
    PENDING_COOKIE_NAME,
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
      typeof value.pendingHandle !== 'string' ||
      !/^[A-Za-z0-9_-]{43}$/.test(value.pendingHandle)
    ) {
      return null
    }
    return value.pendingHandle
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
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
