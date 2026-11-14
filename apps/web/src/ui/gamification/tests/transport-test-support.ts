import axios, { type InternalAxiosRequestConfig } from 'axios'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type PropsWithChildren } from 'react'
import { vi } from 'vitest'

export const REQUEST_ID = '6e1c92a9-6232-4f21-9427-641b4e34f70a'
export const telemetry = { emit: vi.fn() }

// Keep the consuming hook, query, service, request factory and Axios mapping real.
// Only the network adapter and server-function invocation runtime are replaced.
export function installGamificationTransport(body: unknown, status = 200) {
  const requests: InternalAxiosRequestConfig[] = []
  const createClient = axios.create.bind(axios)
  vi.spyOn(axios, 'create').mockImplementation((config) =>
    createClient({
      ...config,
      adapter: async (request) => {
        requests.push(request)
        return { data: body, status, statusText: '', headers: {}, config: request }
      },
    }),
  )
  return requests
}

export function createTestServerFn() {
  const builder = {
    middleware: () => builder,
    validator: () => builder,
    handler:
      (handler: (input: unknown) => Promise<unknown>) =>
      (input: { data?: unknown } = {}) =>
        handler({ ...input, context: { requestId: REQUEST_ID, telemetry } }),
  }
  return builder
}

export function createQueryWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return function QueryWrapper({ children }: PropsWithChildren) {
    return createElement(QueryClientProvider, { client }, children)
  }
}
