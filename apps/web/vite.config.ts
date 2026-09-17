import { defineConfig, loadEnv } from 'vite'
import { fileURLToPath } from 'node:url'
import { devtools } from '@tanstack/devtools-vite'

import { tanstackStart } from '@tanstack/react-start/plugin/vite'

import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const APP_ENV_DIR = fileURLToPath(new URL('.', import.meta.url))

const config = defineConfig(({ mode }) => {
  const env = loadEnv(mode, APP_ENV_DIR, '')

  return {
    resolve: { tsconfigPaths: true },
    server: { port: Number(env.SHIFU_WEB_APP_PORT) || 7000 },
    plugins: [devtools(), tailwindcss(), tanstackStart(), viteReact()],
  }
})

export default config
