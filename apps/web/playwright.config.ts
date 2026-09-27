import { defineConfig } from '@playwright/test'
import { loadEnv } from 'vite'

const port = process.env.SHIFU_WEB_APP_PORT ?? '7000'
const identityPort = process.env.SHIFU_SERVER_APP_PORT ?? '7777'
const env = loadEnv(process.env.NODE_ENV ?? 'development', process.cwd(), '')
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ?? env.SHIFU_WEB_APP_URL ?? `http://127.0.0.1:${port}`
const identityURL =
  process.env.SHIFU_IDENTITY_API_URL ?? `http://127.0.0.1:${identityPort}`

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  globalTimeout: 15 * 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL,
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  webServer: [
    {
      command: `uv run uvicorn main:app --app-dir src --host 127.0.0.1 --port ${identityPort}`,
      cwd: '../server',
      env: {
        REDIS_URL: process.env.REDIS_URL ?? 'redis://localhost:6379/0',
      },
      url: `${identityURL}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: `corepack pnpm dev -- --host 0.0.0.0 --port ${port}`,
      env: {
        SHIFU_IDENTITY_API_URL: identityURL,
        SHIFU_TRUSTED_PROXY_IPS: '127.0.0.1,::1',
      },
      url: `${baseURL}/login/`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
})
