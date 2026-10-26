import { createServer, request as proxyRequest } from 'node:http'

const port = Number(process.env.SHIFU_ACCOUNT_TEST_PROXY_PORT)
const identityOrigin = process.env.SHIFU_ACCOUNT_TEST_IDENTITY_ORIGIN
if (!port || !identityOrigin)
  throw new Error(
    'The account upstream requires a loopback port and real Identity origin',
  )

const scenarios = new Map()
const server = createServer((request, response) => {
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
      scenarios.set(accountId, { hits: {} })
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
    scenario &&
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
  request.pipe(upstream)
})
server.listen(port, '127.0.0.1')
function close() {
  server.close()
  server.closeAllConnections()
}
process.on('SIGTERM', close)
process.on('SIGINT', close)
