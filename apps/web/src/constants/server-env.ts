import { z } from 'zod'

import { AppError } from '@/core/errors/app-error'

const TELEMETRY_ENVIRONMENTS = ['dev', 'local', 'staging', 'production'] as const
const TELEMETRY_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR'] as const

const SERVER_ENV_SCHEMA = z.object({
  shifuServerAppUrl: z.string().url().default('http://localhost:7777'),
  telemetryEnvironment: z.enum(TELEMETRY_ENVIRONMENTS),
  telemetryLogLevel: z.enum(TELEMETRY_LEVELS),
  releaseVersion: z.string().min(1),
  bffSharedSecret: z.string().min(1),
})

const telemetryEnvironment =
  process.env.SHIFU_WEB_APP_MODE ??
  (process.env.NODE_ENV === 'production' ? 'production' : 'local')
const releaseVersion = process.env.SHIFU_RELEASE_VERSION?.trim()

if (
  (telemetryEnvironment === 'staging' || telemetryEnvironment === 'production') &&
  !releaseVersion
) {
  throw new AppError('SHIFU_RELEASE_VERSION é obrigatório neste ambiente.')
}

const bffSharedSecret = process.env.SHIFU_BFF_SHARED_SECRET?.trim()

if (process.env.NODE_ENV === 'production' && !bffSharedSecret) {
  throw new AppError('SHIFU_BFF_SHARED_SECRET é obrigatório neste ambiente.')
}

const SERVER_ENV_INPUT = {
  // The FastAPI app is a single deployable serving Identity, Learning and
  // Intelligence alike; this is the existing name for its base URL.
  shifuServerAppUrl: process.env.SHIFU_IDENTITY_API_URL,
  telemetryEnvironment,
  telemetryLogLevel: process.env.SHIFU_WEB_APP_LOG_LEVEL ?? 'INFO',
  releaseVersion: releaseVersion ?? 'local-dev',
  // The API skips its per-address request limit for calls carrying this secret.
  bffSharedSecret: bffSharedSecret || 'shifu-local-bff-shared-secret-change-me',
}

export const SERVER_ENV = SERVER_ENV_SCHEMA.parse(SERVER_ENV_INPUT)
