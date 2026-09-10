import Axios, { type AxiosInstance } from 'axios'
import type {
  RestClient,
  RestClientRequestConfig,
} from '@/core/global/interfaces/rest-client'
import { RestResponse } from '@/core/global/responses/rest-response'

export const createAxiosRestClient = (baseUrl = ''): RestClient => {
  const axios: AxiosInstance = Axios.create({
    baseURL: baseUrl,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  return {
    async get<T>(
      url: string,
      config?: RestClientRequestConfig,
    ): Promise<RestResponse<T>> {
      try {
        const res = await axios.get<T>(url, config)
        return new RestResponse<T>({
          body: res.data,
          statusCode: res.status,
        })
      } catch (err: any) {
        return new RestResponse<T>({
          errorMessage: err.response?.data?.message || err.message,
          statusCode: err.response?.status || 500,
        })
      }
    },

    async post<T>(
      url: string,
      body?: unknown,
      config?: RestClientRequestConfig,
    ): Promise<RestResponse<T>> {
      try {
        const res = await axios.post<T>(url, body, config)
        return new RestResponse<T>({
          body: res.data,
          statusCode: res.status,
        })
      } catch (err: any) {
        return new RestResponse<T>({
          errorMessage: err.response?.data?.message || err.message,
          statusCode: err.response?.status || 500,
        })
      }
    },

    async patch<T>(
      url: string,
      body?: unknown,
      config?: RestClientRequestConfig,
    ): Promise<RestResponse<T>> {
      try {
        const res = await axios.patch<T>(url, body, config)
        return new RestResponse<T>({
          body: res.data,
          statusCode: res.status,
        })
      } catch (err: any) {
        return new RestResponse<T>({
          errorMessage: err.response?.data?.message || err.message,
          statusCode: err.response?.status || 500,
        })
      }
    },

    async put<T>(
      url: string,
      body?: unknown,
      config?: RestClientRequestConfig,
    ): Promise<RestResponse<T>> {
      try {
        const res = await axios.put<T>(url, body, config)
        return new RestResponse<T>({
          body: res.data,
          statusCode: res.status,
        })
      } catch (err: any) {
        return new RestResponse<T>({
          errorMessage: err.response?.data?.message || err.message,
          statusCode: err.response?.status || 500,
        })
      }
    },

    async delete(url: string, config?: RestClientRequestConfig): Promise<RestResponse> {
      try {
        const res = await axios.delete(url, config)
        return new RestResponse({
          statusCode: res.status,
        })
      } catch (err: any) {
        return new RestResponse({
          errorMessage: err.response?.data?.message || err.message,
          statusCode: err.response?.status || 500,
        })
      }
    },
  }
}
