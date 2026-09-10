export function normalizeHeaders(headers: unknown): Record<string, string> {
  if (!headers || typeof headers !== 'object') return {}

  const headersWithJson = headers as {
    toJSON?: () => Record<string, unknown>
  }
  const source = headersWithJson.toJSON?.() ?? (headers as Record<string, unknown>)

  return Object.entries(source).reduce(
    (normalizedHeaders, [key, value]) => {
      if (value !== undefined && value !== null) {
        normalizedHeaders[key] = Array.isArray(value) ? value.join(', ') : String(value)
      }

      return normalizedHeaders
    },
    {} as Record<string, string>,
  )
}
