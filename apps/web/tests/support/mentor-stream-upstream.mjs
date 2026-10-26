import { createServer, request as proxyRequest } from 'node:http'

const port = Number(process.env.SHIFU_MENTOR_STREAM_TEST_PROXY_PORT)
const identityOrigin = process.env.SHIFU_MENTOR_STREAM_IDENTITY_ORIGIN
if (!port || !identityOrigin)
  throw new Error(
    'The controlled Mentor upstream requires a port and real Identity origin',
  )
const scenarios = new Map()
const gamificationScenarios = new Map()
const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? '/', `http://127.0.0.1:${port}`)
  if (url.pathname === '/__mentor-control/health') {
    response.end('ready')
    return
  }
  const control =
    /^\/__mentor-control\/([0-9A-HJKMNP-TV-Z]{26})(?:\/(release|observations))?$/.exec(
      url.pathname,
    )
  if (control) {
    const [, sessionId, action] = control
    if (request.method === 'POST' && !action) {
      let text = ''
      for await (const chunk of request) text += chunk
      const config = JSON.parse(text)
      scenarios.set(sessionId, {
        ...config,
        calls: 0,
        cancelCalls: 0,
        closed: false,
        ended: false,
        upstreamAuthorization: false,
        upstreamCookie: false,
        cursor: null,
        authorizedAccount: null,
        response: null,
      })
      response.end('registered')
      return
    }
    const scenario = scenarios.get(sessionId)
    if (!scenario) {
      response.writeHead(404)
      response.end()
      return
    }
    if (request.method === 'POST' && action === 'release') {
      scenario.ended = true
      scenario.response?.end(scenario.finalChunk ?? '')
      response.end('released')
      return
    }
    if (request.method === 'GET' && action === 'observations') {
      const { response: privateResponse, ...observations } = scenario
      void privateResponse
      response.setHeader('Content-Type', 'application/json')
      response.end(JSON.stringify(observations))
      return
    }
    if (request.method === 'DELETE') {
      scenario.response?.destroy()
      scenarios.delete(sessionId)
      response.end('removed')
      return
    }
    response.writeHead(405)
    response.end()
    return
  }
  const cancellation =
    /^\/intelligence\/mentor-sessions\/([0-9A-HJKMNP-TV-Z]{26})\/responses\/[^/]+\/cancel$/.exec(
      url.pathname,
    )
  if (cancellation && scenarios.has(cancellation[1])) {
    scenarios.get(cancellation[1]).cancelCalls += 1
    response.writeHead(409)
    response.end()
    return
  }
  const events =
    /^\/intelligence\/mentor-sessions\/([0-9A-HJKMNP-TV-Z]{26})\/events$/.exec(
      url.pathname,
    )
  if (events) {
    const scenario = scenarios.get(events[1])
    if (!scenario) {
      response.writeHead(404)
      response.end()
      return
    }
    scenario.calls += 1
    scenario.upstreamAuthorization = /^Bearer /.test(request.headers.authorization ?? '')
    scenario.upstreamCookie = Boolean(request.headers.cookie)
    scenario.cursor = request.headers['last-event-id'] ?? null
    const access = await fetch(`${identityOrigin}/identity/session`, {
      headers: { Authorization: request.headers.authorization ?? '' },
    })
    if (!access.ok) {
      response.writeHead(access.status)
      response.end('Private auth diagnostics must not escape')
      return
    }
    const account = await access.json()
    scenario.authorizedAccount = account.account_id
    if (account.account_id !== scenario.ownerAccountId) {
      response.writeHead(404)
      response.end('Private foreign context must not escape')
      return
    }
    if (scenario.status && scenario.status !== 200) {
      response.writeHead(scenario.status, {
        'Set-Cookie': 'provider-secret=never-forward',
        Authorization: 'Bearer upstream-private',
        'X-Provider-Secret': 'never-forward',
        'Cache-Control': 'public',
      })
      response.end('Private provider diagnostics must not escape')
      return
    }
    scenario.response = response
    response.on('close', () => {
      scenario.closed = true
    })
    response.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-store',
      'Set-Cookie': 'provider-secret=never-forward',
      Authorization: 'Bearer upstream-private',
      'X-Provider-Secret': 'never-forward',
    })
    response.flushHeaders()
    const bytes = Buffer.from(scenario.initialChunk ?? '')
    // One-byte writes intentionally split UTF-8 codepoints and SSE field lines.
    let offset = 0
    function writeFragment() {
      if (response.destroyed || offset === bytes.length) return
      response.write(bytes.subarray(offset, ++offset))
      setImmediate(writeFragment)
    }
    writeFragment()
    return
  }
  const gamificationControl =
    /^\/__gamification-control\/([0-9A-Z]{26})(?:\/(observations))?$/.exec(url.pathname)
  if (gamificationControl) {
    const accountId = gamificationControl[1]
    if (request.method === 'POST' && !gamificationControl[2]) {
      let text = ''
      for await (const chunk of request) text += chunk
      const config = JSON.parse(text)
      gamificationScenarios.set(accountId, { ...config, observations: [] })
      response.end('registered')
      return
    }
    if (request.method === 'DELETE') {
      gamificationScenarios.delete(accountId)
      response.end('removed')
      return
    }
    const scenario = gamificationScenarios.get(accountId)
    if (request.method === 'GET' && gamificationControl[2] && scenario) {
      response.setHeader('Content-Type', 'application/json')
      response.end(JSON.stringify(scenario.observations))
      return
    }
    response.writeHead(404)
    response.end()
    return
  }
  const configuredPath = `${url.pathname}${url.search}`
  if (
    (url.pathname.startsWith('/gamification/') ||
      url.pathname.startsWith('/learning/')) &&
    [...gamificationScenarios.values()].some((scenario) =>
      Object.hasOwn(scenario.responses, configuredPath),
    )
  ) {
    const authorization = request.headers.authorization ?? ''
    const access = await fetch(`${identityOrigin}/identity/session`, {
      headers: { Authorization: authorization },
    })
    if (!access.ok) {
      response.writeHead(access.status)
      response.end()
      return
    }
    const identity = await access.json()
    const scenario = gamificationScenarios.get(identity.account_id)
    const configured = scenario?.responses[configuredPath]
    if (!configured) {
      response.writeHead(404)
      response.end()
      return
    }
    scenario.observations.push({
      method: request.method,
      path: configuredPath,
      authorization: authorization.startsWith('Bearer '),
      cookie: Boolean(request.headers.cookie),
      bffMark: Boolean(request.headers['x-shifu-bff-secret']),
      accountId: identity.account_id,
      status: configured.status ?? 200,
    })
    response.writeHead(configured.status ?? 200, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify(configured.body))
    return
  }
  // Identity remains real: forward method, cookie/auth headers and exact body.
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
  for (const scenario of scenarios.values()) scenario.response?.destroy()
  server.close()
  server.closeAllConnections()
}
process.on('SIGTERM', close)
process.on('SIGINT', close)
