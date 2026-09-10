import axios from 'axios'

import { request } from '@/rest/axios/utils'
import type { RestClient, RestRequestOptions } from '@/core/shared/interfaces/rest-client'

const REST_REQUEST_TIMEOUT_MS = 15_000

export const AxiosRestClient = (baseUrl?: string): RestClient => {
  const client = axios.create({
    baseURL: baseUrl,
    timeout: REST_REQUEST_TIMEOUT_MS,
    withCredentials: true,
  })

  function get<ResponseBody>(url: string, options: RestRequestOptions) {
    return request<ResponseBody>(client, {
      method: 'get',
      url,
      params: options?.params,
    })
  }

  return {
    get,

    getFile(url) {
      return request<File>(client, {
        method: 'get',
        url,
        responseType: 'blob',
      })
    },

    post<ResponseBody>(url: string, body?: unknown) {
      return request<ResponseBody>(client, {
        method: 'post',
        url,
        data: body,
      })
    },

    postFormData<ResponseBody>(url: string, body: FormData) {
      return request<ResponseBody>(client, {
        method: 'post',
        url,
        data: body,
      })
    },

    patch<ResponseBody>(url: string, body?: unknown) {
      return request<ResponseBody>(client, {
        method: 'patch',
        url,
        data: body,
      })
    },

    put<ResponseBody>(url: string, body?: unknown) {
      return request<ResponseBody>(client, {
        method: 'put',
        url,
        data: body,
      })
    },

    delete<ResponseBody>(url: string, body?: unknown) {
      return request<ResponseBody>(client, {
        method: 'delete',
        url,
        data: body,
      })
    },
  }
}
