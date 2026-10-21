import { createElement, type ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

import { useGoalsListSection } from '../use-goals-list-section'

const mocks = vi.hoisted(() => ({ getCurrentAccess: vi.fn(), get: vi.fn() }))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    handler: (handler: () => Promise<unknown>) => () => handler(),
  }),
}))
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://shifu.test'),
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))
vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: () => ({ get: mocks.get }),
}))

const GOAL = {
  id: '01J00000000000000000000001',
  title: 'Aprender React',
  description: 'Construir interfaces',
  skillCount: 2,
  updatedAt: '2026-10-21T12:00:00Z',
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return renderHook(() => useGoalsListSection(), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
}

describe('useGoalsListSection routed Goal list consumer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.get.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: { goals: [GOAL] } }),
    )
  })
  afterEach(cleanup)

  it('loads the account Goals and presents the singular count', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.state).toBe('populated'))
    expect(result.current.goals).toEqual([GOAL])
    expect(result.current.goalsCountLabel).toBe('1 objetivo')
    expect(mocks.get).toHaveBeenCalledWith('/learning/goals', {
      headers: { Authorization: 'Bearer test-token' },
    })
  })

  it('recovers the same Goal list after a transient HTTP failure', async () => {
    mocks.get
      .mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
      .mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.state).toBe('error'), {
      timeout: 4000,
    })
    act(() => result.current.handleRetry())
    await waitFor(() => expect(result.current.state).toBe('populated'))
    expect(result.current.goals).toEqual([GOAL])
  })
})
