import type { RestResponse } from '@/core/shared/responses/rest-response'

export type RestRequestOptions = {
  params?: Record<
    string,
    string | number | boolean | readonly (string | number)[] | undefined
  >
  headers?: Record<string, string>
  signal?: AbortSignal
}

export interface RestClient {
  get<ResponseBody>(
    url: string,
    options?: RestRequestOptions,
  ): Promise<RestResponse<ResponseBody>>
  getFile(url: string, options?: RestRequestOptions): Promise<RestResponse<Blob>>
  post<ResponseBody>(
    url: string,
    body?: unknown,
    options?: RestRequestOptions,
  ): Promise<RestResponse<ResponseBody>>
  postFormData<ResponseBody>(
    url: string,
    body: FormData,
    options?: RestRequestOptions,
  ): Promise<RestResponse<ResponseBody>>
  patch<ResponseBody>(
    url: string,
    body?: unknown,
    options?: RestRequestOptions,
  ): Promise<RestResponse<ResponseBody>>
  put<ResponseBody>(
    url: string,
    body?: unknown,
    options?: RestRequestOptions,
  ): Promise<RestResponse<ResponseBody>>
  delete<ResponseBody>(
    url: string,
    body?: unknown,
    options?: RestRequestOptions,
  ): Promise<RestResponse<ResponseBody>>
}
