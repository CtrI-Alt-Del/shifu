import type { RestStreamClient } from '@/core/shared/interfaces/rest-stream-client'
import { RestResponse } from '@/core/shared/responses/rest-response'
export const FetchRestStreamClient = (baseUrl: string): RestStreamClient => ({
  async getStream(url, options) {
    try {
      const response = await fetch(`${baseUrl.replace(/\/$/, '')}${url}`, {
        headers: options.headers,
        signal: options.signal,
        cache: 'no-store',
        redirect: 'error',
      })
      return new RestResponse({
        statusCode: response.status,
        body: response.ok ? (response.body ?? undefined) : undefined,
        errorMessage: 'Não foi possível acompanhar a resposta. Tente novamente.',
      })
    } catch {
      return new RestResponse({
        statusCode: 0,
        errorMessage: 'Não foi possível acompanhar a resposta. Tente novamente.',
      })
    }
  },
})
