export function getErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === 'string') return data

  if (data && typeof data === 'object') {
    const responseData = data as Record<string, unknown>
    const message = responseData.message ?? responseData.error

    if (typeof message === 'string') return message
    if (Array.isArray(message)) return message.join(', ')
  }

  return fallback
}
