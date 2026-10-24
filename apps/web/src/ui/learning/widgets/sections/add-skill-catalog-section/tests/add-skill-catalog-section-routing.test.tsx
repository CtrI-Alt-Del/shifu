import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

import { AddSkillCatalogSection } from '..'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
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
vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: () => ({ get: mocks.get, post: mocks.post }),
}))

const GOAL_ID = '01J00000000000000000000001'
const SKILL_ID = '01J00000000000000000000002'
const FOUNDATION_ID = '01J00000000000000000000003'
const CATALOG_SKILL = {
  id: SKILL_ID,
  name: 'React',
  description: 'Criar interfaces',
  alreadyInGoal: false,
  skillExperienceId: null,
  foundations: [{ skillId: FOUNDATION_ID, name: 'JavaScript', status: 'missing' }],
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <AddSkillCatalogSection goalId={GOAL_ID} />
    </QueryClientProvider>,
  )
}

describe('AddSkillCatalogSection routed catalog consumer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mocks.get.mockResolvedValue(
      new RestResponse({
        statusCode: 200,
        body: { items: [CATALOG_SKILL], nextCursor: null },
      }),
    )
    mocks.post.mockResolvedValue(
      new RestResponse({ statusCode: 201, body: { created: [] } }),
    )
  })
  afterEach(cleanup)

  it('loads available Skills for the Goal and submits only the selected foundation', async () => {
    setup()
    await waitFor(() => expect(screen.getByText('React')).toBeVisible())
    expect(mocks.get).toHaveBeenCalledWith(`/learning/goals/${GOAL_ID}/skills/catalog`, {
      params: { query: undefined, cursor: undefined, limit: 20 },
      headers: { Authorization: 'Bearer test-token' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^Adicionar$/ }))
    expect(screen.getByRole('heading', { name: 'Adicionar: React' })).toBeVisible()
    fireEvent.click(screen.getByRole('checkbox', { name: /JavaScript/ }))
    const confirmationButton = screen.getAllByRole('button', {
      name: /^Adicionar$/,
    })[1]
    if (!confirmationButton) throw new Error('Expected foundation confirmation control')
    fireEvent.click(confirmationButton)
    await waitFor(() => expect(mocks.post).toHaveBeenCalledOnce())
    expect(mocks.post).toHaveBeenCalledWith(
      `/learning/goals/${GOAL_ID}/skills`,
      { skill_id: SKILL_ID, foundation_skill_ids: [FOUNDATION_ID] },
      { headers: { Authorization: 'Bearer test-token' } },
    )
    await waitFor(() =>
      expect(
        screen.queryByRole('heading', { name: 'Adicionar: React' }),
      ).not.toBeInTheDocument(),
    )
  })

  it('shows the server catalog failure and hides addition controls', async () => {
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    setup()
    await waitFor(() =>
      expect(screen.getByText(/Não foi possível concluir a solicitação/)).toBeVisible(),
    )
    expect(screen.queryByRole('button', { name: /^Adicionar$/ })).not.toBeInTheDocument()
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it('keeps the selected Skill dialog open with a visible rejected addition', async () => {
    mocks.post.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    setup()
    await waitFor(() => expect(screen.getByText('React')).toBeVisible())
    fireEvent.click(screen.getByRole('button', { name: /^Adicionar$/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /JavaScript/ }))
    const confirmationButton = screen.getAllByRole('button', {
      name: /^Adicionar$/,
    })[1]
    if (!confirmationButton) throw new Error('Expected foundation confirmation control')
    fireEvent.click(confirmationButton)
    await waitFor(() =>
      expect(screen.getByText('Não foi possível concluir a solicitação.')).toBeVisible(),
    )
    expect(screen.getByRole('heading', { name: 'Adicionar: React' })).toBeVisible()
    expect(mocks.post).toHaveBeenCalledWith(
      `/learning/goals/${GOAL_ID}/skills`,
      { skill_id: SKILL_ID, foundation_skill_ids: [FOUNDATION_ID] },
      { headers: { Authorization: 'Bearer test-token' } },
    )
  })
})
