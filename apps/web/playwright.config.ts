import { defineConfig } from '@playwright/test'
import { loadEnv } from 'vite'

const port = process.env.SHIFU_WEB_APP_PORT ?? '7000'
const env = loadEnv(process.env.NODE_ENV ?? 'development', process.cwd(), '')
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ?? env.SHIFU_WEB_APP_URL ?? `http://127.0.0.1:${port}`

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL,
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${port}`,
    url: `${baseURL}/login/`,
    reuseExistingServer: !process.env.CI,
  },
})
