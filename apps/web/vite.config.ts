import { defineConfig, loadEnv, type Plugin } from 'vite'
import { fileURLToPath } from 'node:url'
import { devtools } from '@tanstack/devtools-vite'

import { tanstackStart } from '@tanstack/react-start/plugin/vite'

import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const APP_ENV_DIR = fileURLToPath(new URL('.', import.meta.url))
const webContainerIsolationHeaders = {
  'Cross-Origin-Embedder-Policy': 'require-corp',
  'Cross-Origin-Opener-Policy': 'same-origin',
}

const webContainerIsolationPlugin: Plugin = {
  name: 'shifu-webcontainer-isolation',
  enforce: 'pre',
  configureServer(server) {
    server.middlewares.use((_request, response, next) => {
      for (const [name, value] of Object.entries(webContainerIsolationHeaders)) {
        response.setHeader(name, value)
      }
      next()
    })
  },
  configurePreviewServer(server) {
    server.middlewares.use((_request, response, next) => {
      for (const [name, value] of Object.entries(webContainerIsolationHeaders)) {
        response.setHeader(name, value)
      }
      next()
    })
  },
}

const config = defineConfig(({ mode }) => {
  const env = loadEnv(mode, APP_ENV_DIR, '')

  return {
    resolve: { tsconfigPaths: true },
    server: {
      port: Number(env.SHIFU_WEB_APP_PORT) || 7000,
      headers: webContainerIsolationHeaders,
    },
    preview: { headers: webContainerIsolationHeaders },
    plugins: [
      webContainerIsolationPlugin,
      ...(process.env.CI ? [] : [devtools()]),
      tailwindcss(),
      tanstackStart(),
      viteReact(),
    ],
  }
})

export default config
