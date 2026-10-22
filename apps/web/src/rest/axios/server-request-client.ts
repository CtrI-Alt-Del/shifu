import { SERVER_ENV } from '@/constants/server-env'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'

import { AxiosRestClient, type AxiosRestClientOptions } from './axios-rest-client'

export type ServerRequestClientOptions = AxiosRestClientOptions &
  Readonly<{
    baseUrl?: string
  }>

export function createServerRequestClient(
  context: RequestTelemetryContext | undefined,
  options: ServerRequestClientOptions = {},
) {
  const { baseUrl = SERVER_ENV.shifuServerAppUrl, ...clientOptions } = options
  return AxiosRestClient(baseUrl, {
    ...clientOptions,
    withCredentials: clientOptions.withCredentials ?? false,
    requestId: context?.requestId,
    telemetry: context?.telemetry,
  })
}
