import { afterEach, describe, expect, it, vi } from 'vitest'

describe('server environment contract', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('uses local defaults and trims the release version', async () => {
    vi.stubEnv('NODE_ENV', 'test')
    vi.stubEnv('SHIFU_WEB_APP_MODE', 'local')
    vi.stubEnv('SHIFU_RELEASE_VERSION', '  local-build  ')
    vi.stubEnv('SHIFU_WEB_APP_LOG_LEVEL', 'DEBUG')

    const { SERVER_ENV } = await import('@/constants/server-env')

    expect(SERVER_ENV).toMatchObject({
      releaseVersion: 'local-build',
      telemetryEnvironment: 'local',
      telemetryLogLevel: 'DEBUG',
    })
  })

  it('requires an explicit release in staging and production', async () => {
    vi.stubEnv('NODE_ENV', 'test')
    vi.stubEnv('SHIFU_WEB_APP_MODE', 'staging')
    vi.stubEnv('SHIFU_RELEASE_VERSION', '')

    await expect(import('@/constants/server-env')).rejects.toThrow(
      'SHIFU_RELEASE_VERSION é obrigatório neste ambiente.',
    )
  })
})
