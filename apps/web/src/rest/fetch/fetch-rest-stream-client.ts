import type { RestStreamClient } from '@/core/shared/interfaces/rest-stream-client'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { RestResponse } from '@/core/shared/responses/rest-response'
import { observeResponseCorrelation } from '@/rest/telemetry/observe-response-correlation'

export const FetchRestStreamClient = (
  baseUrl: string,
  context?: RequestTelemetryContext,
): RestStreamClient => ({
  async getStream(url, options) {
    const headers = {
      ...options.headers,
      ...(context?.requestId ? { 'X-Request-ID': context.requestId } : {}),
    }
    try {
      const response = await fetch(`${baseUrl.replace(/\/$/, '')}${url}`, {
        headers,
        signal: options.signal,
        cache: 'no-store',
        redirect: 'error',
      })
      observeResponseCorrelation(context?.telemetry, {
        method: 'GET',
        requestId: context?.requestId,
        responseRequestId: response.headers.get('X-Request-ID') ?? undefined,
        statusCode: response.status,
      })
      return new RestResponse({
        statusCode: response.status,
        body: response.ok ? (response.body ?? undefined) : undefined,
        errorMessage: 'Não foi possível acompanhar a resposta. Tente novamente.',
      })
    } catch {
      observeResponseCorrelation(context?.telemetry, {
        method: 'GET',
        requestId: context?.requestId,
        statusCode: 0,
      })
      return new RestResponse({
        statusCode: 0,
        errorMessage: 'Não foi possível acompanhar a resposta. Tente novamente.',
      })
    }
  },
})
