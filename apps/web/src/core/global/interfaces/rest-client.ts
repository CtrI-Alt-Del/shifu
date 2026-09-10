import type { RestResponse } from '../responses/rest-response'

export type RestClientRequestConfig = {
  responseType?: 'json' | 'blob' | 'arraybuffer'
  headers?: Record<string, string>
}

export interface RestClient {
  get<ResponseBody>(
    url: string,
    config?: RestClientRequestConfig,
  ): Promise<RestResponse<ResponseBody>>
  post<ResponseBody>(
    url: string,
    body?: unknown,
    config?: RestClientRequestConfig,
  ): Promise<RestResponse<ResponseBody>>
  patch<ResponseBody>(
    url: string,
    body?: unknown,
    config?: RestClientRequestConfig,
  ): Promise<RestResponse<ResponseBody>>
  put<ResponseBody>(
    url: string,
    body?: unknown,
    config?: RestClientRequestConfig,
  ): Promise<RestResponse<ResponseBody>>
  delete(url: string, config?: RestClientRequestConfig): Promise<RestResponse>
}
