import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/integration',
  use: {
    baseURL: 'http://127.0.0.1:6000',
    launchOptions: { args: ['--explicitly-allowed-ports=6000'] },
  },
  webServer: {
    command: 'pnpm dev --host 127.0.0.1',
    url: 'http://127.0.0.1:6000/account/',
    reuseExistingServer: !process.env.CI,
  },
})
