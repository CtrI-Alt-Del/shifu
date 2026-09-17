import { AppError } from '@/core/errors/app-error'

const SESSION_LIFETIME_SECONDS = 30 * 24 * 60 * 60
const RATE_LIMIT_WINDOW_SECONDS = 5 * 60
const RATE_LIMIT_MAX_REQUESTS = 10

export type BetterAuthSettings = {
  baseURL: string
  databaseURL: string
  identityURL: string
  secret: string
  trustedProxyIPs: string[]
  useSecureCookies: boolean
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

export const BetterAuthConfig = (): BetterAuthSettings => {
  const baseURL =
    process.env.SHIFU_WEB_APP_URL ??
    `http://localhost:${process.env.SHIFU_WEB_APP_PORT ?? '7000'}`
  const databaseURL =
    process.env.BETTER_AUTH_DATABASE_URL ??
    process.env.DATABASE_URL?.replace('+psycopg', '') ??
    'postgresql://shifu:shifu-local@localhost:54344/shifu'
  const identityURL = process.env.SHIFU_IDENTITY_API_URL ?? 'http://localhost:7777'
  const secret = process.env.BETTER_AUTH_SECRET ?? process.env.AUTH_SECRET

  if (process.env.NODE_ENV === 'production' && !secret) {
    throw new AppError('A configuração segura de autenticação não está disponível.')
  }

  return {
    baseURL,
    databaseURL,
    identityURL,
    secret: secret ?? 'shifu-local-better-auth-secret-change-me-32-chars',
    trustedProxyIPs: readTrustedProxyIPs(),
    useSecureCookies: process.env.NODE_ENV === 'production',
  }
}

export const BETTER_AUTH_OPTIONS = {
  sessionLifetimeSeconds: SESSION_LIFETIME_SECONDS,
  rateLimitWindowSeconds: RATE_LIMIT_WINDOW_SECONDS,
  rateLimitMaxRequests: RATE_LIMIT_MAX_REQUESTS,
}
