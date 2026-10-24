import { createElement, type ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

import { useGoalCreatePage } from '../use-goal-create-page'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
  navigate: vi.fn(),
}))

vi.mock('@tanstack/react-router', () => ({ useNavigate: () => mocks.navigate }))
vi.mock('@tanstack/react-start', () => ({
  createStart: () => ({}),
  createMiddleware: () => ({ server: (handler: unknown) => handler }),
  createServerFn: () => ({
    middleware: () => ({
      handler:
        (handler: (context: { context: { requestId: string } }) => Promise<unknown>) =>
        () =>
          handler({ context: { requestId: 'test-request-id' } }),
      validator: (validate: (data: unknown) => unknown) => ({
        handler:
          (handler: (context: { data: unknown }) => Promise<unknown>) =>
          (context: { data: unknown }) =>
            handler({
              data: validate(context.data),
              context: { requestId: 'test-request-id' },
            } as never),
      }),
    }),
    handler:
      (handler: (context: { context: { requestId: string } }) => Promise<unknown>) =>
      () =>
        handler({ context: { requestId: 'test-request-id' } }),
    validator: (validate: (data: unknown) => unknown) => ({
      handler:
        (handler: (context: { data: unknown }) => Promise<unknown>) =>
        (context: { data: unknown }) =>
          handler({ data: validate(context.data) }),
    }),
  }),
}))
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://shifu.test'),
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))
vi.mock('@/provision/auth/better-auth/better-auth-config', () => ({
  BetterAuthConfig: () => ({ identityURL: 'http://shifu.test' }),
}))
vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: () => ({ get: mocks.get, post: mocks.post }),
}))

const SKILL_ID = '01J00000000000000000000001'
const GOAL_ID = '01J00000000000000000000002'
const SKILL = {
  id: SKILL_ID,
  name: 'React',
  available: true,
  unavailableReason: null,
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return renderHook(() => useGoalCreatePage(), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
}

async function completeForm(result: ReturnType<typeof setup>['result']) {
  act(() => {
    result.current.setTitle('  Aprender React  ')
    result.current.setDescription('  Criar interfaces  ')
    result.current.handleToggleSkill(SKILL_ID)
  })
  await act(async () => result.current.handleSubmit({ preventDefault: vi.fn() } as never))
}

describe('useGoalCreatePage routed goal consumers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.get.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: { skills: [SKILL] } }),
    )
    mocks.post.mockResolvedValue(
      new RestResponse({
        statusCode: 201,
        body: { goalId: GOAL_ID, skillIds: [SKILL_ID] },
      }),
    )
  })
  afterEach(cleanup)

  it('loads available Skills and creates a Goal with trimmed fields and the selected Skill', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.skills).toEqual([SKILL]))
    expect(mocks.get).toHaveBeenCalledWith('/learning/available-skills', {
      headers: { Authorization: 'Bearer test-token' },
    })

    await completeForm(result)

    expect(mocks.post).toHaveBeenCalledWith(
      '/learning/goals',
      {
        title: 'Aprender React',
        description: 'Criar interfaces',
        skillIds: [SKILL_ID],
      },
      { headers: { Authorization: 'Bearer test-token' } },
    )
    expect(mocks.navigate).toHaveBeenCalledWith({
      to: '/learning/goals/$goalId',
      params: { goalId: GOAL_ID },
    })
    expect(result.current.submissionError).toBeNull()
  })

  it('keeps the Goal form when the server reports a Curriculum gap', async () => {
    mocks.post.mockResolvedValue(
      new RestResponse({ statusCode: 409, body: { code: 'curriculum_gap' } }),
    )
    const { result } = setup()
    await waitFor(() => expect(result.current.skills).toHaveLength(1))
    await completeForm(result)
    expect(result.current.submissionError).toContain('Revise a seleção')
    expect(result.current.title).toBe('  Aprender React  ')
    expect(result.current.selectedSkillIds).toEqual([SKILL_ID])
    expect(mocks.navigate).not.toHaveBeenCalled()
  })

  it('shows a retryable Skill loading failure without submitting the form', async () => {
    mocks.get.mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.hasSkillsError).toBe(true))
    await act(async () => result.current.handleRetrySkills())
    await waitFor(() => expect(result.current.skills).toEqual([SKILL]))
    expect(result.current.hasSkillsError).toBe(false)
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it('preserves entered fields after an unavailable creation response', async () => {
    mocks.post.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.skills).toHaveLength(1))
    await completeForm(result)
    expect(result.current.submissionError).toContain('Seus dados continuam aqui')
    expect(result.current.description).toBe('  Criar interfaces  ')
    expect(mocks.navigate).not.toHaveBeenCalled()
  })
})
