import { defineConfig } from '@playwright/test'
import { loadEnv } from 'vite'

const port = process.env.SHIFU_WEB_APP_PORT ?? '7000'
const identityPort = process.env.SHIFU_SERVER_APP_PORT ?? '7777'
const env = loadEnv(process.env.NODE_ENV ?? 'development', process.cwd(), '')
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ?? env.SHIFU_WEB_APP_URL ?? `http://127.0.0.1:${port}`
const identityURL =
  process.env.SHIFU_IDENTITY_API_URL ?? `http://127.0.0.1:${identityPort}`
const mentorProxyPort = process.env.SHIFU_MENTOR_STREAM_TEST_PROXY_PORT
const mentorProxyURL = mentorProxyPort ? `http://127.0.0.1:${mentorProxyPort}` : null
const mentorProxyServers = mentorProxyURL
  ? [
      {
        command: 'exec node tests/support/mentor-stream-upstream.mjs',
        env: {
          SHIFU_MENTOR_STREAM_TEST_PROXY_PORT: mentorProxyPort as string,
          SHIFU_MENTOR_STREAM_IDENTITY_ORIGIN: identityURL,
        },
        url: `${mentorProxyURL}/__mentor-control/health`,
        reuseExistingServer: false,
        timeout: 30_000,
      },
    ]
  : []
const webServerCommand = `exec ./node_modules/.bin/vite dev --host 0.0.0.0 --port ${port}${mentorProxyURL ? ' --strictPort' : ''}`

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  globalTimeout: 15 * 60_000,
  expect: {
    timeout: 10_000,
  },

  reporter: process.env.CI
    ? [['line'], ['html', { outputFolder: 'playwright-report', open: 'never' }]]
    : 'list',
  use: {
    baseURL,
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },

  webServer: [
    {
      command: `exec .venv/bin/uvicorn main:app --app-dir src --host 127.0.0.1 --port ${identityPort}`,
      cwd: '../server',
      env: {
        REDIS_URL: process.env.REDIS_URL ?? 'redis://localhost:6379/0',
      },
      url: `${identityURL}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    ...mentorProxyServers,
    {
      command: webServerCommand,
      env: {
        SHIFU_IDENTITY_API_URL: mentorProxyURL ?? identityURL,
        SHIFU_TRUSTED_PROXY_IPS: '127.0.0.1,::1',
      },
      url: `${baseURL}/login/`,
      reuseExistingServer: mentorProxyURL ? false : !process.env.CI,
      timeout: 60_000,
    },
  ],
})
