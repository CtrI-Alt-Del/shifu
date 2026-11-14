import axios from 'axios'

import { RestResponse } from '@/core/shared/responses/rest-response'
import type { TelemetryProvider } from '@/core/shared/interfaces/telemetry-provider'
import { request } from '@/rest/axios/utils'
import { observeResponseCorrelation } from '@/rest/telemetry/observe-response-correlation'
import type { RestClient, RestRequestOptions } from '@/core/shared/interfaces/rest-client'

const REST_REQUEST_TIMEOUT_MS = 15_000

export type AxiosRestClientOptions = {
  defaultHeaders?: Record<string, string>
  requestId?: string
  telemetry?: TelemetryProvider
  withCredentials?: boolean
}

export const AxiosRestClient = (
  baseUrl?: string,
  options: AxiosRestClientOptions = {},
): RestClient => {
  const client = axios.create({
    baseURL: baseUrl,
    timeout: REST_REQUEST_TIMEOUT_MS,
    withCredentials: options.withCredentials ?? true,
  })
  const defaultHeaders = {
    ...options.defaultHeaders,
    ...(options.requestId ? { 'X-Request-ID': options.requestId } : {}),
  }

  async function execute<ResponseBody>(
    method: string,
    config: Parameters<typeof request<ResponseBody>>[1],
  ): Promise<RestResponse<ResponseBody>> {
    const response = await request<ResponseBody>(client, config)
    const responseRequestId = Object.entries(response.headers ?? {}).find(
      ([key]) => key.toLowerCase() === 'x-request-id',
    )?.[1]
    observeResponseCorrelation(options.telemetry, {
      method,
      requestId: options.requestId,
      responseRequestId,
      statusCode: response.statusCode,
    })
    return response
  }

  function get<ResponseBody>(url: string, requestOptions: RestRequestOptions) {
    return execute<ResponseBody>('GET', {
      method: 'get',
      url,
      params: requestOptions?.params,
      headers: { ...defaultHeaders, ...requestOptions?.headers },
    })
  }

  return {
    get,

    async getFile(url, requestOptions) {
      const response = await execute<ArrayBuffer>('GET', {
        method: 'get',
        url,
        params: requestOptions?.params,
        headers: { ...defaultHeaders, ...requestOptions?.headers },
        signal: requestOptions?.signal,
        // Axios' Node adapter decodes `blob` responses as text. Use raw bytes
        // here because this client also runs in the server-side BFF.
        responseType: 'arraybuffer',
      })
      if (response.isFailure)
        return new RestResponse<Blob>({
          statusCode: response.statusCode,
          headers: response.headers,
          errorMessage: response.errorMessage,
        })

      return new RestResponse<Blob>({
        body: new Blob([response.body]),
        statusCode: response.statusCode,
        headers: response.headers,
      })
    },

    post<ResponseBody>(url: string, body?: unknown, requestOptions?: RestRequestOptions) {
      return execute<ResponseBody>('POST', {
        method: 'post',
        url,
        data: body,
        headers: { ...defaultHeaders, ...requestOptions?.headers },
      })
    },

    postFormData<ResponseBody>(
      url: string,
      body: FormData,
      requestOptions?: RestRequestOptions,
    ) {
      return execute<ResponseBody>('POST', {
        method: 'post',
        url,
        data: body,
        headers: { ...defaultHeaders, ...requestOptions?.headers },
        signal: requestOptions?.signal,
      })
    },

    patch<ResponseBody>(
      url: string,
      body?: unknown,
      requestOptions?: RestRequestOptions,
    ) {
      return execute<ResponseBody>('PATCH', {
        method: 'patch',
        url,
        data: body,
        headers: { ...defaultHeaders, ...requestOptions?.headers },
      })
    },

    put<ResponseBody>(url: string, body?: unknown, requestOptions?: RestRequestOptions) {
      return execute<ResponseBody>('PUT', {
        method: 'put',
        url,
        data: body,
        headers: { ...defaultHeaders, ...requestOptions?.headers },
      })
    },

    delete<ResponseBody>(
      url: string,
      body?: unknown,
      requestOptions?: RestRequestOptions,
    ) {
      return execute<ResponseBody>('DELETE', {
        method: 'delete',
        url,
        data: body,
        headers: { ...defaultHeaders, ...requestOptions?.headers },
      })
    },
  }
}
