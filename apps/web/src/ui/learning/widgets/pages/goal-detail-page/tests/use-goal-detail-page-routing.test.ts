import { createElement, type ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

import { useGoalDetailPage } from '../use-goal-detail-page'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  get: vi.fn(),
  delete: vi.fn(),
  navigateTo: vi.fn(),
}))

vi.mock('@tanstack/react-start', () => ({
  createStart: () => ({}),
  createMiddleware: () => ({ server: (handler: unknown) => handler }),
  createServerFn: () => ({
    middleware: () => ({
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
  AxiosRestClient: () => ({ get: mocks.get, delete: mocks.delete }),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: () => ({ navigateTo: mocks.navigateTo }),
}))

const GOAL_ID = '01J00000000000000000000001'
const SKILL_ID = '01J00000000000000000000002'
const DETAIL = {
  goalId: GOAL_ID,
  title: 'Aprender React',
  description: 'Praticar interfaces',
  skills: [
    {
      skillExperienceId: '01J00000000000000000000003',
      skillId: SKILL_ID,
      name: 'React',
      status: 'learning',
      progress: 40,
      inclusionReason: null,
    },
  ],
  relations: [],
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return renderHook(() => useGoalDetailPage({ goalId: GOAL_ID }), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
}

describe('useGoalDetailPage routed goal consumers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: DETAIL }))
    mocks.delete.mockResolvedValue(new RestResponse({ statusCode: 204 }))
  })
  afterEach(cleanup)

  it('reads the private Goal detail and presents its Skills', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.state).toBe('success'))
    expect(result.current.detail?.title).toBe('Aprender React')
    expect(result.current.detail?.skills[0]?.name).toBe('React')
    expect(mocks.get).toHaveBeenCalledWith(`/learning/goals/${GOAL_ID}`, {
      headers: { Authorization: 'Bearer test-token' },
    })
  })

  it.each([
    [404, 'not-found'],
    [503, 'error'],
  ] as const)(
    'classifies HTTP %s as %s without stale Goal detail',
    async (statusCode, state) => {
      mocks.get.mockResolvedValue(new RestResponse({ statusCode }))
      const { result } = setup()
      await waitFor(() => expect(result.current.state).toBe(state))
      expect(result.current.detail).toBeNull()
    },
  )

  it('deletes the selected Goal and navigates home only after server success', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.state).toBe('success'))
    act(() => result.current.handleOpenConfirmDialog())
    expect(result.current.isConfirmDialogOpen).toBe(true)
    act(() => result.current.handleConfirmRemoval())
    await waitFor(() => expect(mocks.navigateTo).toHaveBeenCalledWith('root'))
    expect(mocks.delete).toHaveBeenCalledWith(`/learning/goals/${GOAL_ID}`, undefined, {
      headers: { Authorization: 'Bearer test-token' },
    })
  })

  it('removes only the selected Skill from the Goal and clears its dialog', async () => {
    const { result } = setup()
    await waitFor(() => expect(result.current.state).toBe('success'))
    const skill = result.current.detail?.skills[0]
    expect(skill).toBeDefined()
    if (!skill) throw new Error('Expected the selected Skill in Goal detail')
    act(() => result.current.handleOpenSkillRemoval(skill))
    await act(async () => result.current.handleConfirmSkillRemoval())
    expect(mocks.delete).toHaveBeenCalledWith(
      `/learning/goals/${GOAL_ID}/skills/${SKILL_ID}`,
      undefined,
      { headers: { Authorization: 'Bearer test-token' } },
    )
    expect(result.current.selectedSkill).toBeNull()
    expect(mocks.navigateTo).not.toHaveBeenCalled()
  })

  it('keeps the Skill removal dialog open after an HTTP failure', async () => {
    mocks.delete.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    const { result } = setup()
    await waitFor(() => expect(result.current.state).toBe('success'))
    const skill = result.current.detail?.skills[0]
    if (!skill) throw new Error('Expected the selected Skill in Goal detail')
    act(() => result.current.handleOpenSkillRemoval(skill))
    await act(async () => result.current.handleConfirmSkillRemoval())
    expect(result.current.selectedSkill).toEqual(skill)
    await waitFor(() =>
      expect(result.current.removeSkillError).toContain('Tente novamente'),
    )
    expect(mocks.navigateTo).not.toHaveBeenCalled()
  })
})
