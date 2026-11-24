import { AppError } from '@/core/errors/app-error'

const SESSION_LIFETIME_SECONDS = 30 * 24 * 60 * 60
const RATE_LIMIT_WINDOW_SECONDS = 5 * 60
const RATE_LIMIT_MAX_REQUESTS = 10

export type BetterAuthSettings = {
  baseURL: string
  bffSharedSecret: string
  databaseURL: string
  identityURL: string
  secret: string
  trustedOrigins: string[]
  trustedProxyIPs: string[]
  useSecureCookies: boolean
}

const LOOPBACK_HOSTS = ['localhost', '127.0.0.1']

// In local development the app is opened as either localhost or 127.0.0.1, so
// both loopback spellings of the base URL are trusted. Production trusts only
// the configured base URL.
export function readTrustedOrigins(baseURL: string): string[] {
  if (process.env.NODE_ENV === 'production') return []

  const url = new URL(baseURL)
  if (!LOOPBACK_HOSTS.includes(url.hostname)) return []

  return LOOPBACK_HOSTS.filter((host) => host !== url.hostname).map(
    (host) => `${url.protocol}//${host}${url.port ? `:${url.port}` : ''}`,
  )
}

function readTrustedProxyIPs() {
  const configured = process.env.SHIFU_TRUSTED_PROXY_IPS
  const value =
    configured ?? (process.env.NODE_ENV === 'production' ? '' : '127.0.0.1,::1')

  return value
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
}

function readUseSecureCookies() {
  const configured = process.env.SHIFU_USE_SECURE_COOKIES

  if (configured === undefined || configured === '') {
    return process.env.NODE_ENV === 'production'
  }

  return configured !== 'false'
}

export const BetterAuthConfig = (): BetterAuthSettings => {
  const baseURL =
    process.env.SHIFU_WEB_APP_URL ??
    `http://localhost:${process.env.SHIFU_WEB_APP_PORT ?? '7000'}`
  const databaseURL =
    process.env.BETTER_AUTH_DATABASE_URL ??
    process.env.DATABASE_URL?.replace('+psycopg', '') ??
    'postgresql://shifu:shifu-local@localhost:54344/shifu'
  const identityURL = process.env.SHIFU_IDENTITY_API_URL ?? 'http://localhost:7777'
  const bffSharedSecret = process.env.SHIFU_BFF_SHARED_SECRET
  const secret = process.env.BETTER_AUTH_SECRET ?? process.env.AUTH_SECRET

  if (process.env.NODE_ENV === 'production' && (!secret || !bffSharedSecret)) {
    throw new AppError('A configuração segura de autenticação não está disponível.')
  }

  return {
    baseURL,
    bffSharedSecret: bffSharedSecret ?? 'shifu-local-bff-shared-secret-change-me',
    databaseURL,
    identityURL,
    secret: secret ?? 'shifu-local-better-auth-secret-change-me-32-chars',
    trustedOrigins: readTrustedOrigins(baseURL),
    trustedProxyIPs: readTrustedProxyIPs(),
    useSecureCookies: readUseSecureCookies(),
  }
}

export const BETTER_AUTH_OPTIONS = {
  sessionLifetimeSeconds: SESSION_LIFETIME_SECONDS,
  rateLimitWindowSeconds: RATE_LIMIT_WINDOW_SECONDS,
  rateLimitMaxRequests: RATE_LIMIT_MAX_REQUESTS,
}
