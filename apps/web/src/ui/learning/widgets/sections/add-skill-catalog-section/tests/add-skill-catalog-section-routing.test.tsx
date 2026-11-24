import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

import { AddSkillCatalogSection } from '..'

const mocks = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('@tanstack/react-start', () => ({
  createCsrfMiddleware: () => ({}),
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
vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: () => ({ get: mocks.get, post: mocks.post }),
}))
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))

type LinkMockProps = Omit<ComponentProps<'a'>, 'href'> & {
  params?: Record<string, string>
  to: string
}

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, params, to, ...props }: LinkMockProps) => (
    <a data-params={JSON.stringify(params)} href={to} {...props}>
      {children}
    </a>
  ),
}))

const GOAL_ID = '01J00000000000000000000001'
const SKILL_ID = '01J00000000000000000000002'
const FOUNDATION_ID = '01J00000000000000000000003'
const OTHER_GOAL_ID = '01J00000000000000000000004'
const SECOND_OTHER_GOAL_ID = '01J00000000000000000000005'
const CATALOG_PATH = `/learning/goals/${GOAL_ID}/skills/catalog`
const EXPERIENCES_PATH = `/learning/skills/${SKILL_ID}/experiences`
const ADD_PATH = `/learning/goals/${GOAL_ID}/skills`
const AUTHORIZATION = { headers: { Authorization: 'Bearer test-token' } }
const CATALOG_SKILL = {
  id: SKILL_ID,
  name: 'React',
  description: 'Criar interfaces',
  alreadyInGoal: false,
  skillExperienceId: null,
  foundations: [{ skillId: FOUNDATION_ID, name: 'JavaScript', status: 'missing' }],
}
const SKILL_WITHOUT_FOUNDATIONS = { ...CATALOG_SKILL, foundations: [] }

function createExperience(goalId: string, goalTitle: string, status: string) {
  return {
    goalId,
    goalTitle,
    skillExperienceId: `exp-${goalId}`,
    skillId: SKILL_ID,
    status,
  }
}

function mockCatalog(skill: typeof CATALOG_SKILL) {
  mocks.get.mockImplementation(async (path: string) => {
    if (path === CATALOG_PATH) {
      return new RestResponse({
        statusCode: 200,
        body: { items: [skill], nextCursor: null },
      })
    }
    if (path === EXPERIENCES_PATH) {
      return new RestResponse({ statusCode: 200, body: { experiences: [] } })
    }
    throw new Error(`Unexpected GET ${path}`)
  })
}

function mockExperiences(response: RestResponse<unknown>) {
  const catalogResponse = new RestResponse({
    statusCode: 200,
    body: { items: [CATALOG_SKILL], nextCursor: null },
  })
  mocks.get.mockImplementation(async (path: string) => {
    if (path === CATALOG_PATH) return catalogResponse
    if (path === EXPERIENCES_PATH) return response
    throw new Error(`Unexpected GET ${path}`)
  })
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <AddSkillCatalogSection goalId={GOAL_ID} />
    </QueryClientProvider>,
  )
}

async function openDialogFor(skillName: string) {
  await waitFor(() => expect(screen.getByText(skillName)).toBeVisible())
  const addButton = screen.getByRole('button', { name: /^Adicionar$/ })
  addButton.focus()
  fireEvent.click(addButton)
  return {
    addButton,
    dialog: await screen.findByRole('dialog', { name: `Adicionar ${skillName}?` }),
  }
}

describe('AddSkillCatalogSection routed catalog consumer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mockCatalog(CATALOG_SKILL)
    mocks.post.mockResolvedValue(
      new RestResponse({ statusCode: 201, body: { created: [] } }),
    )
  })
  afterEach(cleanup)

  it('loads available Skills for the Goal and submits only the selected foundation', async () => {
    setup()
    const { dialog } = await openDialogFor('React')

    expect(mocks.get).toHaveBeenCalledWith(CATALOG_PATH, {
      params: { query: undefined, cursor: undefined, limit: 20 },
      ...AUTHORIZATION,
    })
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /JavaScript/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Adicionar habilidade' }))

    await waitFor(() => expect(mocks.post).toHaveBeenCalledOnce())
    expect(mocks.post).toHaveBeenCalledWith(
      ADD_PATH,
      { skill_id: SKILL_ID, foundation_skill_ids: [FOUNDATION_ID] },
      AUTHORIZATION,
    )
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('adds a Skill without any selected foundation', async () => {
    mockCatalog(SKILL_WITHOUT_FOUNDATIONS)
    setup()
    const { dialog } = await openDialogFor('React')

    expect(
      within(dialog).getByText(
        'Esta Habilidade não possui bases sugeridas no Currículo.',
      ),
    ).toBeVisible()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Adicionar habilidade' }))

    await waitFor(() => expect(mocks.post).toHaveBeenCalledOnce())
    expect(mocks.post).toHaveBeenCalledWith(
      ADD_PATH,
      { skill_id: SKILL_ID, foundation_skill_ids: [] },
      AUTHORIZATION,
    )
  })

  it('shows the server catalog failure and recovers through the retry action', async () => {
    mocks.get.mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
    setup()
    await waitFor(() =>
      expect(screen.getByText(/Não foi possível concluir a solicitação/)).toBeVisible(),
    )
    expect(screen.queryByRole('button', { name: /^Adicionar$/ })).not.toBeInTheDocument()
    expect(mocks.post).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    await waitFor(() => expect(screen.getByText('React')).toBeVisible())
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(mocks.get).toHaveBeenCalledTimes(2)
  })

  it('keeps the selected Skill dialog open with a visible rejected addition', async () => {
    mocks.post.mockResolvedValue(new RestResponse({ statusCode: 503 }))
    setup()
    const { dialog } = await openDialogFor('React')
    fireEvent.click(within(dialog).getByRole('checkbox', { name: /JavaScript/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Adicionar habilidade' }))

    await waitFor(() =>
      expect(
        within(dialog).getByText('Não foi possível concluir a solicitação.'),
      ).toBeVisible(),
    )
    expect(screen.getByRole('dialog', { name: 'Adicionar React?' })).toBeVisible()
    expect(within(dialog).getByRole('checkbox', { name: /JavaScript/ })).toBeChecked()
    expect(mocks.post).toHaveBeenCalledWith(
      ADD_PATH,
      { skill_id: SKILL_ID, foundation_skill_ids: [FOUNDATION_ID] },
      AUTHORIZATION,
    )
  })

  it('names each other Goal in the notice and excludes the destination Goal', async () => {
    mockExperiences(
      new RestResponse({
        statusCode: 200,
        body: {
          experiences: [
            createExperience(GOAL_ID, 'Este Objetivo', 'not-started'),
            createExperience(OTHER_GOAL_ID, 'Carreira em dados', 'completed'),
            createExperience(SECOND_OTHER_GOAL_ID, 'Dados na prática', 'learning'),
          ],
        },
      }),
    )
    setup()
    const { dialog } = await openDialogFor('React')

    const notice = await within(dialog).findByRole('region', {
      name: 'Você já tem esta Habilidade em outro Objetivo',
    })
    expect(mocks.get).toHaveBeenCalledWith(EXPERIENCES_PATH, AUTHORIZATION)
    expect(notice).toHaveTextContent(
      'No Objetivo “Carreira em dados”, ela está concluída.',
    )
    expect(notice).toHaveTextContent(
      'No Objetivo “Dados na prática”, ela está em aprendizado.',
    )
    expect(notice).not.toHaveTextContent('Este Objetivo')
    expect(
      within(notice).getByRole('link', { name: 'Ver em Carreira em dados' }),
    ).toHaveAttribute(
      'data-params',
      JSON.stringify({ goalId: OTHER_GOAL_ID, skillId: SKILL_ID }),
    )

    fireEvent.click(within(dialog).getByRole('button', { name: 'Adicionar habilidade' }))
    await waitFor(() => expect(mocks.post).toHaveBeenCalledOnce())
  })

  it('shows no notice when the Skill exists only in the destination Goal', async () => {
    mockExperiences(
      new RestResponse({
        statusCode: 200,
        body: { experiences: [createExperience(GOAL_ID, 'Este Objetivo', 'learning')] },
      }),
    )
    setup()
    const { dialog } = await openDialogFor('React')

    await waitFor(() =>
      expect(mocks.get).toHaveBeenCalledWith(EXPERIENCES_PATH, AUTHORIZATION),
    )
    expect(
      within(dialog).queryByText('Você já tem esta Habilidade em outro Objetivo'),
    ).not.toBeInTheDocument()
  })

  it('shows no notice and still adds when the experiences lookup fails', async () => {
    mockExperiences(new RestResponse({ statusCode: 503 }))
    setup()
    const { dialog } = await openDialogFor('React')

    await waitFor(() =>
      expect(mocks.get).toHaveBeenCalledWith(EXPERIENCES_PATH, AUTHORIZATION),
    )
    expect(
      within(dialog).queryByText('Você já tem esta Habilidade em outro Objetivo'),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Adicionar habilidade' }))
    await waitFor(() => expect(mocks.post).toHaveBeenCalledOnce())
  })

  it('closes the dialog with Escape and returns focus to the Skill action', async () => {
    setup()
    const { addButton, dialog } = await openDialogFor('React')

    fireEvent.keyDown(dialog, { key: 'Escape' })

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await waitFor(() => expect(addButton).toHaveFocus())
    expect(mocks.post).not.toHaveBeenCalled()
  })
})
