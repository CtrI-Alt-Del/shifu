// Shifu service worker: shows the streak reminder push and opens Shifu on click.
// It holds no authentication logic; routing decides between the app and the entry flow.

const DEFAULT_TITLE = 'Shifu'
const DEFAULT_URL = '/'

function readPayload(event) {
  if (!event.data) return {}
  try {
    const payload = event.data.json()
    const isRecord =
      payload !== null && typeof payload === 'object' && !Array.isArray(payload)
    return isRecord ? payload : {}
  } catch {
    return {}
  }
}

function readText(value) {
  return typeof value === 'string' && value ? value : undefined
}

function resolveSameOriginUrl(url) {
  const fallbackUrl = new URL(DEFAULT_URL, self.location.origin).href
  if (typeof url !== 'string') return fallbackUrl
  try {
    const target = new URL(url, self.location.origin)
    return target.origin === self.location.origin ? target.href : fallbackUrl
  } catch {
    return fallbackUrl
  }
}

self.addEventListener('install', () => {
  // A freshly registered worker takes over without waiting for the tab to close.
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  const payload = readPayload(event)

  event.waitUntil(
    self.registration.showNotification(readText(payload.title) ?? DEFAULT_TITLE, {
      body: readText(payload.body),
      tag: readText(payload.tag),
      icon: '/favicon.svg',
      data: { url: readText(payload.url) ?? DEFAULT_URL },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = resolveSameOriginUrl(event.notification.data?.url)

  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        const sameOriginClient = windowClients.find(
          (windowClient) => new URL(windowClient.url).origin === self.location.origin,
        )
        if (!sameOriginClient) return self.clients.openWindow(targetUrl)

        // An uncontrolled tab cannot be navigated; a new window is the fallback.
        return sameOriginClient
          .focus()
          .then((focusedClient) =>
            (focusedClient || sameOriginClient).navigate(targetUrl),
          )
          .catch(() => self.clients.openWindow(targetUrl))
      }),
  )
})
