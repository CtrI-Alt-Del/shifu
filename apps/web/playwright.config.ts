import { defineConfig } from '@playwright/test'

const port = process.env.SHIFU_WEB_APP_PORT ?? '7000'
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${port}`

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
