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
const ERASURE_ACK_UNAVAILABLE_SCENARIO = 'account-erasure-ack-unavailable'
const ERASURE_TARGET_GONE_SCENARIO = 'account-erasure-target-gone'
const PENDING_STATUS_SCENARIO = 'pending-status-unavailable'
const PENDING_STATUS_INVALID_SCENARIO = 'pending-status-invalid'
const GLOBAL_SCENARIO_ID = '00000000000000000000000000'
const QUOTA_REFUSED_ROUTES = [
  /^\/intelligence\/mentor-sessions\/?$/,
  /^\/intelligence\/mentor-sessions\/[^/]+\/messages\/?$/,
  /^\/intelligence\/mentor-sessions\/[^/]+\/responses\/[^/]+\/retry\/?$/,
  /^\/intelligence\/planning-sessions\/?$/,
  /^\/intelligence\/planning-sessions\/[^/]+\/(?:restart|retry)\/?$/,
]
const scenarios = new Map()
const erasureOwners = new Map()
async function readScenarioKind(request) {
  let text = ''
  for await (const chunk of request) text += chunk
  if (!text) return FAULT_SCENARIO
  try {
    const scenario = JSON.parse(text).scenario
    return [
      QUOTA_SCENARIO,
      ERASURE_ACK_UNAVAILABLE_SCENARIO,
      ERASURE_TARGET_GONE_SCENARIO,
      PENDING_STATUS_SCENARIO,
      PENDING_STATUS_INVALID_SCENARIO,
    ].includes(scenario)
      ? scenario
      : FAULT_SCENARIO
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
  const control = /^\/__account-control\/([^/]+)$/.exec(url.pathname)
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
  if (request.method === 'POST' && url.pathname === '/identity/account-deletions') {
    const chunks = []
    request.on('data', (chunk) => chunks.push(chunk))
    request.on('end', () => {
      try {
        const erasureId = JSON.parse(Buffer.concat(chunks).toString()).erasure_id
        if (typeof erasureId === 'string' && accountId) {
          erasureOwners.set(erasureId, accountId)
        }
      } catch {
        // Invalid requests are handled by the real Identity API.
      }
    })
  }
  const erasureTarget = /^\/identity\/internal\/account-erasures\/([^/]+)\/target$/.exec(
    url.pathname,
  )
  const erasureAcknowledgement =
    /^\/identity\/internal\/account-erasures\/([^/]+)\/acknowledgements$/.exec(
      url.pathname,
    )
  const erasureOwnerId = erasureTarget?.[1] ?? erasureAcknowledgement?.[1]
  const erasureOwner = erasureOwnerId ? erasureOwners.get(erasureOwnerId) : undefined
  const erasureScenario = erasureOwner ? scenarios.get(erasureOwner) : undefined
  if (erasureTarget && erasureScenario?.kind === ERASURE_TARGET_GONE_SCENARIO) {
    request.resume()
    response.writeHead(404, {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
    })
    response.end(JSON.stringify({ code: 'not_found' }))
    return
  }
  if (
    erasureAcknowledgement &&
    erasureScenario?.kind === ERASURE_ACK_UNAVAILABLE_SCENARIO
  ) {
    request.resume()
    response.writeHead(503, {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
    })
    response.end(JSON.stringify({ code: 'service_unavailable' }))
    return
  }
  let pendingHandle
  let bufferedBody
  if (url.pathname === '/identity/pending-confirmations/status') {
    const chunks = []
    for await (const chunk of request) chunks.push(chunk)
    bufferedBody = Buffer.concat(chunks)
    try {
      pendingHandle = JSON.parse(bufferedBody.toString()).pending_handle
    } catch {
      pendingHandle = undefined
    }
  }
  const scenario =
    scenarios.get(accountId) ??
    scenarios.get(pendingHandle) ??
    scenarios.get(GLOBAL_SCENARIO_ID)
  if (
    scenario?.kind === PENDING_STATUS_SCENARIO &&
    url.pathname === '/identity/pending-confirmations/status'
  ) {
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
  if (
    scenario?.kind === PENDING_STATUS_INVALID_SCENARIO &&
    url.pathname === '/identity/pending-confirmations/status'
  ) {
    response.writeHead(200, {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
    })
    response.end(JSON.stringify({ state: 'unknown', hasPendingContext: true }))
    return
  }
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
  if (bufferedBody) upstream.end(bufferedBody)
  else request.pipe(upstream)
})
server.listen(port, '127.0.0.1')
function close() {
  server.close()
  server.closeAllConnections()
}
process.on('SIGTERM', close)
process.on('SIGINT', close)
