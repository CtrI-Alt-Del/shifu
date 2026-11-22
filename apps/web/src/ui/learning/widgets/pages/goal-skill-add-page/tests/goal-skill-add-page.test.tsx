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

import type { CatalogSkill } from '@/core/learning/catalog-skill'
import { RestResponse } from '@/core/shared/responses/rest-response'

import { GoalSkillAddPage } from '..'

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
const LOGIC_SKILL_ID = '01J00000000000000000000002'
const CATALOG_PATH = `/learning/goals/${GOAL_ID}/skills/catalog`
const EXPERIENCES_PATH = `/learning/skills/${LOGIC_SKILL_ID}/experiences`
const AUTHORIZATION = { headers: { Authorization: 'Bearer test-token' } }

const SKILLS: CatalogSkill[] = [
  {
    id: LOGIC_SKILL_ID,
    name: 'Lógica de programação',
    description: 'Variáveis, condicionais, repetição e funções.',
    alreadyInGoal: false,
    skillExperienceId: null,
    foundations: [],
  },
  {
    id: '01J00000000000000000000003',
    name: 'SQL básico',
    description: 'Consultas, filtros e junções.',
    alreadyInGoal: true,
    skillExperienceId: '01J00000000000000000000009',
    foundations: [],
  },
]

function mockCatalog(items: CatalogSkill[], nextCursor: string | null = null) {
  mocks.get.mockImplementation(async (path: string) => {
    if (path === CATALOG_PATH) {
      return new RestResponse({ statusCode: 200, body: { items, nextCursor } })
    }
    if (path === EXPERIENCES_PATH) {
      return new RestResponse({ statusCode: 200, body: { experiences: [] } })
    }
    throw new Error(`Unexpected GET ${path}`)
  })
}

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <GoalSkillAddPage goalId={GOAL_ID} />
    </QueryClientProvider>,
  )
}

describe('GoalSkillAddPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({
      accountId: 'account-1',
      accessToken: 'test-token',
    })
    mockCatalog(SKILLS)
    mocks.post.mockResolvedValue(
      new RestResponse({ statusCode: 201, body: { created: [] } }),
    )
  })
  afterEach(cleanup)

  it('renders the back link, the heading, the search field and the catalog in that order', async () => {
    setup()

    const backLink = screen.getByRole('link', { name: 'Voltar ao Objetivo' })
    const heading = screen.getByRole('heading', {
      level: 1,
      name: 'Adicionar Habilidade',
    })
    const search = screen.getByRole('textbox', { name: 'Buscar no Currículo' })
    const firstSkill = await screen.findByRole('heading', {
      name: 'Lógica de programação',
    })

    expect(heading).toBeVisible()
    expect(backLink.compareDocumentPosition(heading)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
    expect(heading.compareDocumentPosition(search)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
    expect(search.compareDocumentPosition(firstSkill)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
  })

  it('links the way back to the Goal', () => {
    setup()

    const backLink = screen.getByRole('link', { name: 'Voltar ao Objetivo' })
    expect(backLink).toHaveAttribute('href', '/learning/goals/$goalId')
    expect(backLink).toHaveAttribute('data-params', JSON.stringify({ goalId: GOAL_ID }))
  })

  it('requests the catalog of the Goal and lists its Skills', async () => {
    setup()

    expect(
      await screen.findByText('Variáveis, condicionais, repetição e funções.'),
    ).toBeVisible()
    expect(mocks.get).toHaveBeenCalledWith(CATALOG_PATH, {
      params: { query: undefined, cursor: undefined, limit: 20 },
      ...AUTHORIZATION,
    })
    expect(screen.getAllByRole('button', { name: 'Adicionar' })).toHaveLength(1)
    expect(screen.getByText('Adicionado')).toBeVisible()
  })

  it('announces the loading state until the catalog answers', async () => {
    let releaseCatalog: () => void = () => undefined
    mocks.get.mockImplementation(
      () =>
        new Promise((resolve) => {
          releaseCatalog = () =>
            resolve(
              new RestResponse({
                statusCode: 200,
                body: { items: SKILLS, nextCursor: null },
              }),
            )
        }),
    )
    setup()

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Carregando habilidades...',
    )
    expect(screen.queryByRole('button', { name: 'Adicionar' })).not.toBeInTheDocument()

    releaseCatalog()

    expect(await screen.findByText('SQL básico')).toBeVisible()
  })

  it('sends the typed search text to the catalog request', async () => {
    setup()
    await screen.findByText('SQL básico')

    fireEvent.change(screen.getByRole('textbox', { name: 'Buscar no Currículo' }), {
      target: { value: 'sql' },
    })

    await waitFor(() =>
      expect(mocks.get).toHaveBeenCalledWith(CATALOG_PATH, {
        params: { query: 'sql', cursor: undefined, limit: 20 },
        ...AUTHORIZATION,
      }),
    )
  })

  it('shows the empty search result', async () => {
    mockCatalog([])
    setup()

    expect(await screen.findByText('Nenhuma habilidade encontrada')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Adicionar' })).not.toBeInTheDocument()
  })

  it('shows the catalog failure as an alert, keeps the way back and retries', async () => {
    mocks.get.mockResolvedValueOnce(new RestResponse({ statusCode: 503 }))
    setup()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível concluir a solicitação',
    )
    expect(screen.getByRole('link', { name: 'Voltar ao Objetivo' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Adicionar' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(await screen.findByText('SQL básico')).toBeVisible()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('loads the next catalog page from the load more action', async () => {
    mockCatalog(SKILLS, 'cursor-2')
    setup()
    await screen.findByText('SQL básico')

    fireEvent.click(screen.getByRole('button', { name: 'Carregar mais' }))

    await waitFor(() =>
      expect(mocks.get).toHaveBeenCalledWith(CATALOG_PATH, {
        params: { query: undefined, cursor: 'cursor-2', limit: 20 },
        ...AUTHORIZATION,
      }),
    )
  })

  it('opens the add dialog for the selected Skill and adds it to the Goal', async () => {
    setup()
    await screen.findByText('Lógica de programação')

    fireEvent.click(screen.getByRole('button', { name: 'Adicionar' }))
    const dialog = await screen.findByRole('dialog', {
      name: 'Adicionar Lógica de programação?',
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Adicionar habilidade' }))

    await waitFor(() => expect(mocks.post).toHaveBeenCalledOnce())
    expect(mocks.post).toHaveBeenCalledWith(
      `/learning/goals/${GOAL_ID}/skills`,
      { skill_id: LOGIC_SKILL_ID, foundation_skill_ids: [] },
      AUTHORIZATION,
    )
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })
})
