import axios from 'axios'

import { RestResponse } from '@/core/shared/responses/rest-response'
import { request } from '@/rest/axios/utils'
import type { RestClient, RestRequestOptions } from '@/core/shared/interfaces/rest-client'

const REST_REQUEST_TIMEOUT_MS = 15_000

export type AxiosRestClientOptions = {
  defaultHeaders?: Record<string, string>
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

  function get<ResponseBody>(url: string, requestOptions: RestRequestOptions) {
    return request<ResponseBody>(client, {
      method: 'get',
      url,
      params: requestOptions?.params,
      headers: { ...options.defaultHeaders, ...requestOptions?.headers },
    })
  }

  return {
    get,

    async getFile(url, requestOptions) {
      const response = await request<ArrayBuffer>(client, {
        method: 'get',
        url,
        params: requestOptions?.params,
        headers: { ...options.defaultHeaders, ...requestOptions?.headers },
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
      return request<ResponseBody>(client, {
        method: 'post',
        url,
        data: body,
        headers: { ...options.defaultHeaders, ...requestOptions?.headers },
      })
    },

    postFormData<ResponseBody>(
      url: string,
      body: FormData,
      requestOptions?: RestRequestOptions,
    ) {
      return request<ResponseBody>(client, {
        method: 'post',
        url,
        data: body,
        headers: { ...options.defaultHeaders, ...requestOptions?.headers },
        signal: requestOptions?.signal,
      })
    },

    patch<ResponseBody>(
      url: string,
      body?: unknown,
      requestOptions?: RestRequestOptions,
    ) {
      return request<ResponseBody>(client, {
        method: 'patch',
        url,
        data: body,
        headers: { ...options.defaultHeaders, ...requestOptions?.headers },
      })
    },

    put<ResponseBody>(url: string, body?: unknown, requestOptions?: RestRequestOptions) {
      return request<ResponseBody>(client, {
        method: 'put',
        url,
        data: body,
        headers: { ...options.defaultHeaders, ...requestOptions?.headers },
      })
    },

    delete<ResponseBody>(
      url: string,
      body?: unknown,
      requestOptions?: RestRequestOptions,
    ) {
      return request<ResponseBody>(client, {
        method: 'delete',
        url,
        data: body,
        headers: { ...options.defaultHeaders, ...requestOptions?.headers },
      })
    },
  }
}
