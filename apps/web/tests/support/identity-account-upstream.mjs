import { createServer, request as proxyRequest } from 'node:http'

const port = Number(process.env.SHIFU_ACCOUNT_TEST_PROXY_PORT)
const identityOrigin = process.env.SHIFU_ACCOUNT_TEST_IDENTITY_ORIGIN
if (!port || !identityOrigin)
  throw new Error(
    'The account upstream requires a loopback port and real Identity origin',
  )

// Per-account scenarios. Without a body, a control POST keeps the original fault:
// 503 on the account routes. `{ "scenario": "ai-quota-exhausted" }` instead answers 429
// to every AI start route and passes everything else through to the real API, so the
// real server functions and their error classification run.
const FAULT_SCENARIO = 'account-unavailable'
const QUOTA_SCENARIO = 'ai-quota-exhausted'
const QUOTA_REFUSED_ROUTES = [
  /^\/intelligence\/mentor-sessions\/?$/,
  /^\/intelligence\/mentor-sessions\/[^/]+\/messages\/?$/,
  /^\/intelligence\/mentor-sessions\/[^/]+\/responses\/[^/]+\/retry\/?$/,
  /^\/intelligence\/planning-sessions\/?$/,
  /^\/intelligence\/planning-sessions\/[^/]+\/(?:restart|retry)\/?$/,
]
const scenarios = new Map()
async function readScenarioKind(request) {
  let text = ''
  for await (const chunk of request) text += chunk
  if (!text) return FAULT_SCENARIO
  try {
    return JSON.parse(text).scenario === QUOTA_SCENARIO ? QUOTA_SCENARIO : FAULT_SCENARIO
  } catch {
    return FAULT_SCENARIO
  }
}
const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? '/', `http://127.0.0.1:${port}`)
  if (url.pathname === '/__account-control/health') {
    response.end('ready')
    return
  }
  const control = /^\/__account-control\/([0-9A-Z]{26})$/.exec(url.pathname)
  if (control) {
    const accountId = control[1]
    response.setHeader('Content-Type', 'application/json')
    if (request.method === 'POST') {
      scenarios.set(accountId, { kind: await readScenarioKind(request), hits: {} })
      response.end(JSON.stringify({ enabled: true }))
    } else if (request.method === 'GET') {
      response.end(JSON.stringify(scenarios.get(accountId) ?? { hits: {} }))
    } else if (request.method === 'DELETE') {
      scenarios.delete(accountId)
      response.end(JSON.stringify({ enabled: false }))
    } else {
      response.writeHead(405)
      response.end('{}')
    }
    return
  }
  // Unverified JWT data selects a test fault only. The real API owns authentication.
  let accountId
  try {
    const token = (request.headers.authorization ?? '').replace(/^Bearer /, '')
    accountId = JSON.parse(
      Buffer.from(token.split('.')[1] ?? '', 'base64url').toString(),
    ).sub
  } catch {
    accountId = undefined
  }
  const scenario = scenarios.get(accountId)
  if (
    scenario?.kind === QUOTA_SCENARIO &&
    request.method === 'POST' &&
    QUOTA_REFUSED_ROUTES.some((route) => route.test(url.pathname))
  ) {
    const key = `${request.method} ${url.pathname}`
    scenario.hits[key] = (scenario.hits[key] ?? 0) + 1
    request.resume()
    response.writeHead(429, {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
    })
    response.end(
      JSON.stringify({
        code: 'ai_quota_exhausted',
        message: 'Sua cota mensal de IA acabou.',
      }),
    )
    return
  }
  if (
    scenario?.kind === FAULT_SCENARIO &&
    [
      '/identity/session',
      '/identity/accounts/me',
      '/identity/accounts/me/password',
    ].includes(url.pathname)
  ) {
    const key = `${request.method} ${url.pathname}`
    scenario.hits[key] = (scenario.hits[key] ?? 0) + 1
    response.writeHead(503, {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
    })
    response.end(
      JSON.stringify({
        code: 'service_unavailable',
        message: 'Serviço temporariamente indisponível.',
      }),
    )
    return
  }
  const target = new URL(`${url.pathname}${url.search}`, identityOrigin)
  const upstream = proxyRequest(
    target,
    { method: request.method, headers: { ...request.headers, host: target.host } },
    (incoming) => {
      response.writeHead(incoming.statusCode ?? 503, incoming.headers)
      incoming.pipe(response)
    },
  )
  upstream.on('error', () => {
    if (!response.headersSent) response.writeHead(503)
    response.end()
  })
  request.on('aborted', () => upstream.destroy())
  response.on('close', () => {
    if (!response.writableFinished) upstream.destroy()
  })
  request.pipe(upstream)
})
server.listen(port, '127.0.0.1')
function close() {
  server.close()
  server.closeAllConnections()
}
process.on('SIGTERM', close)
process.on('SIGINT', close)
