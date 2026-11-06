import { serve } from 'srvx'
import { serveStatic } from 'srvx/static'

import server from './dist/server/server.js'

const PORT = Number(process.env.SHIFU_WEB_APP_PORT) || 7000
const CLIENT_DIR = new URL('./dist/client', import.meta.url).pathname

// The vite dev and preview servers add these headers, so the production server
// must too. The in-browser code runner (WebContainer) needs cross-origin isolation.
const ISOLATION_HEADERS = {
  'Cross-Origin-Embedder-Policy': 'require-corp',
  'Cross-Origin-Opener-Policy': 'same-origin',
}

const IMMUTABLE_CACHE_CONTROL = 'public, max-age=31536000, immutable'

async function addResponseHeaders(request, next) {
  const response = await next()
  const headers = new Headers(response.headers)

  for (const [name, value] of Object.entries(ISOLATION_HEADERS)) {
    headers.set(name, value)
  }

  // Build output under /assets has a content hash in the file name.
  const { pathname } = new URL(request.url)
  if (pathname.startsWith('/assets/') && response.ok) {
    headers.set('Cache-Control', IMMUTABLE_CACHE_CONTROL)
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  })
}

serve({
  port: PORT,
  hostname: '0.0.0.0',
  middleware: [addResponseHeaders, serveStatic({ dir: CLIENT_DIR })],
  fetch: (request) => server.fetch(request),
})
