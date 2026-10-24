import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import { LearnerMemoryFaker } from '@/core/intelligence/fakers/learner-memory-faker'
import type { LearnerMemory } from '@/core/intelligence/learner-memory'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { MemoriesPage } from '..'
import { useMemoriesPage } from '../use-memories-page'

vi.mock('../use-memories-page', () => ({ useMemoriesPage: vi.fn() }))
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, search, ...props }: AnchorProps) => {
    const query = new URLSearchParams(
      Object.entries(search ?? {}).flatMap(([key, value]) =>
        value === undefined ? [] : [[key, String(value)]],
      ),
    ).toString()
    return (
      <a href={`${ROUTES[route]}${query ? `?${query}` : ''}`} {...props}>
        {typeof children === 'function' ? children({ isActive: false }) : children}
      </a>
    )
  },
}))
vi.mock('@xyflow/react', () => ({
  Background: () => null,
  Handle: () => null,
  Position: { Top: 'top' },
  ReactFlow: (props: {
    nodes: { id: string; type: string; data: unknown }[]
    nodeTypes: Record<
      string,
      (nodeProps: { id: string; data: unknown }) => React.ReactNode
    >
  }) => (
    <div>
      {props.nodes.map((node) => {
        const NodeComponent = props.nodeTypes[node.type]
        return NodeComponent ? (
          <NodeComponent data={node.data} id={node.id} key={node.id} />
        ) : null
      })}
    </div>
  ),
}))

const useMemoriesPageMock = vi.mocked(useMemoriesPage)
const handlers = {
  handleQueryChange: vi.fn(),
  handleCategoryChange: vi.fn(),
  handleViewChange: vi.fn(),
  handleClearFilters: vi.fn(),
  handleSelectMemory: vi.fn(),
  handleCloseDetails: vi.fn(),
  handleRetry: vi.fn(),
  handleStartEdit: vi.fn(),
  handleCancelEdit: vi.fn(),
  handleSaveEdit: vi.fn(),
  handleRequestDelete: vi.fn(),
  handleCancelDelete: vi.fn(),
  handleConfirmDelete: vi.fn(),
}

const memories: LearnerMemory[] = [
  LearnerMemoryFaker.fake({
    id: '01J7T8AC91Z5K8M4JQ8C2D6F01',
    category: 'recurring_difficulty',
    content: 'Confundo exibir e retornar valores.',
    createdAt: '2026-10-04T15:00:00Z',
    updatedAt: '2026-10-04T15:00:00Z',
    origins: [
      LearnerMemoryFaker.fakeOrigin({
        sessionId: '01J7T8AC91Z5K8M4JQ8C2D6FA1',
        messageId: '01J7T8AC91Z5K8M4JQ8C2D6FB1',
        conversationTitle: 'Dúvida no laço for',
      }),
      LearnerMemoryFaker.fakeOrigin({
        sessionId: '01J7T8AC91Z5K8M4JQ8C2D6FA2',
        messageId: null,
        conversationTitle: null,
        isAvailable: false,
      }),
    ],
    concepts: [
      { key: 'funcao', label: 'Funções' },
      { key: 'retorno', label: 'Retorno de valores' },
    ],
  }),
  LearnerMemoryFaker.fake({
    id: '01J7T8AC91Z5K8M4JQ8C2D6F02',
    category: 'explanation_preference',
    content: 'Prefiro exemplos curtos em JavaScript.',
    createdAt: '2026-10-03T15:00:00Z',
    updatedAt: '2026-10-05T15:00:00Z',
    version: 2,
  }),
]

function buildPage(overrides: Partial<ReturnType<typeof useMemoriesPage>> = {}) {
  return {
    memories,
    selectedMemory: null,
    query: '',
    category: null,
    view: 'list' as const,
    totalCount: memories.length,
    listStatus: 'ready' as const,
    sidePanelStatus: 'none' as const,
    isLoadingSelectedMemory: false,
    isSaving: false,
    saveError: null,
    conflictContent: null,
    isDeleteDialogOpen: false,
    isDeleting: false,
    deleteError: null,
    ...handlers,
    ...overrides,
  } satisfies ReturnType<typeof useMemoriesPage>
}

describe('MemoriesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMemoriesPageMock.mockReturnValue(buildPage())
  })
  afterEach(cleanup)

  it('renders the header, the way back to the Mentor and the filters', () => {
    render(<MemoriesPage />)

    expect(screen.getByRole('heading', { level: 1, name: 'Memórias' })).toBeVisible()
    expect(
      screen.getByText('O que o Mentor lembra para adaptar as explicações a você.'),
    ).toBeVisible()
    expect(screen.getByRole('link', { name: 'Voltar ao Mentor' })).toHaveAttribute(
      'href',
      ROUTES.intelligence,
    )
    expect(screen.getByRole('searchbox', { name: 'Buscar memórias' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Todas · 2' })).toBeVisible()
  })

  it('shows the skeleton while loading and keeps the filters usable', () => {
    useMemoriesPageMock.mockReturnValue(
      buildPage({ memories: [], listStatus: 'loading', totalCount: null }),
    )
    render(<MemoriesPage />)

    expect(screen.getByText('Carregando memórias.')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Buscar memórias' })).toBeEnabled()
    expect(
      screen.queryByRole('list', { name: 'Lista de memórias' }),
    ).not.toBeInTheDocument()
  })

  it('shows a recoverable error with a retry action', async () => {
    const user = userEvent.setup()
    useMemoriesPageMock.mockReturnValue(
      buildPage({ memories: [], listStatus: 'error', totalCount: null }),
    )
    render(<MemoriesPage />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível carregar suas memórias',
    )
    await user.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(handlers.handleRetry).toHaveBeenCalledOnce()
  })

  it('explains an empty account without a clear-filters action', () => {
    useMemoriesPageMock.mockReturnValue(
      buildPage({ memories: [], listStatus: 'empty', totalCount: 0 }),
    )
    render(<MemoriesPage />)

    expect(
      screen.getByRole('heading', { name: 'Você ainda não tem memórias' }),
    ).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Limpar filtros' }),
    ).not.toBeInTheDocument()
  })

  it('explains an empty filtered result and clears the filters', async () => {
    const user = userEvent.setup()
    useMemoriesPageMock.mockReturnValue(
      buildPage({
        memories: [],
        listStatus: 'empty-filtered',
        query: 'xyz',
        totalCount: 0,
      }),
    )
    render(<MemoriesPage />)

    expect(
      screen.getByRole('heading', { name: 'Nenhuma memória encontrada' }),
    ).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Limpar filtros' }))

    expect(handlers.handleClearFilters).toHaveBeenCalledOnce()
  })

  it('lists the memories with category and provenance and selects one', async () => {
    const user = userEvent.setup()
    useMemoriesPageMock.mockReturnValue(
      buildPage({ selectedMemory: memories[0] ?? null }),
    )
    render(<MemoriesPage />)
    const list = screen.getByRole('list', { name: 'Lista de memórias' })

    const rows = within(list).getAllByRole('button')
    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveAttribute('aria-pressed', 'true')
    expect(rows[1]).toHaveAttribute('aria-pressed', 'false')
    expect(rows[0]).toHaveTextContent('Dificuldades recorrentes')
    expect(rows[0]).toHaveTextContent('Declarada por você · 4 out 2026')
    expect(rows[1]).toHaveTextContent('Declarada por você · atualizada em 5 out 2026')
    await user.click(rows[1] as HTMLElement)

    expect(handlers.handleSelectMemory).toHaveBeenCalledWith(memories[1]?.id)
  })

  it('renders the same memories in the map view', async () => {
    const user = userEvent.setup()
    useMemoriesPageMock.mockReturnValue(buildPage({ view: 'map' }))
    render(<MemoriesPage />)

    expect(screen.getByRole('region', { name: 'Mapa de memórias' })).toBeVisible()
    expect(
      screen.queryByRole('list', { name: 'Lista de memórias' }),
    ).not.toBeInTheDocument()
    const node = screen.getByRole('button', {
      name: 'Preferência de explicação: Prefiro exemplos curtos em JavaScript.',
    })
    await user.click(node)

    expect(handlers.handleSelectMemory).toHaveBeenCalledWith(memories[1]?.id)
    expect(screen.getByRole('tab', { name: 'Mapa' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })

  it('switches the view and the category through the filters', async () => {
    const user = userEvent.setup()
    render(<MemoriesPage />)

    await user.click(screen.getByRole('tab', { name: 'Mapa' }))
    await user.click(screen.getByRole('button', { name: 'Conhecimento declarado' }))

    expect(handlers.handleViewChange).toHaveBeenCalledWith('map')
    expect(handlers.handleCategoryChange).toHaveBeenCalledWith('declared_knowledge')
  })

  it('shows the details with origins, concepts and the proficiency note', async () => {
    const user = userEvent.setup()
    useMemoriesPageMock.mockReturnValue(
      buildPage({ selectedMemory: memories[0] ?? null, sidePanelStatus: 'details' }),
    )
    render(<MemoriesPage />)
    const details = screen.getByRole('region', { name: 'Detalhes da memória' })

    expect(within(details).getByText('Dificuldade recorrente')).toBeVisible()
    expect(
      within(details).getByRole('heading', {
        level: 2,
        name: 'Confundo exibir e retornar valores.',
      }),
    ).toBeVisible()
    expect(
      within(details).getByText(/Declarada por você · criada em 4 out 2026/),
    ).toBeVisible()
    expect(within(details).getByText(/Atualizada em 4 out 2026, às/)).toBeVisible()
    expect(
      within(details).getByRole('link', { name: 'Dúvida no laço for' }),
    ).toHaveAttribute(
      'href',
      `${ROUTES.intelligence}?session=01J7T8AC91Z5K8M4JQ8C2D6FA1&message=01J7T8AC91Z5K8M4JQ8C2D6FB1`,
    )
    expect(within(details).getByText('Conversa excluída')).toBeVisible()
    expect(within(details).getAllByRole('link')).toHaveLength(1)
    expect(within(details).getByText('Funções')).toBeVisible()
    expect(within(details).getByText('Retorno de valores')).toBeVisible()
    expect(
      within(details).getByText(
        'Esta memória orienta explicações; não altera sua proficiência.',
      ),
    ).toBeVisible()
    await user.click(within(details).getByRole('button', { name: 'Editar' }))
    await user.click(within(details).getByRole('button', { name: 'Excluir' }))
    await user.click(
      within(details).getByRole('button', { name: 'Fechar detalhes da memória' }),
    )

    expect(handlers.handleStartEdit).toHaveBeenCalledOnce()
    expect(handlers.handleRequestDelete).toHaveBeenCalledOnce()
    expect(handlers.handleCloseDetails).toHaveBeenCalledOnce()
  })

  it('omits the related-concepts section for a memory without concepts', () => {
    useMemoriesPageMock.mockReturnValue(
      buildPage({ selectedMemory: memories[1] ?? null, sidePanelStatus: 'details' }),
    )
    render(<MemoriesPage />)

    expect(screen.queryByText('Relacionada a')).not.toBeInTheDocument()
  })

  it('opens an origin without a message as a plain conversation link', () => {
    const memory = LearnerMemoryFaker.fake({
      origins: [
        LearnerMemoryFaker.fakeOrigin({
          sessionId: '01J7T8AC91Z5K8M4JQ8C2D6FA3',
          messageId: null,
          conversationTitle: null,
          isAvailable: true,
        }),
      ],
    })
    useMemoriesPageMock.mockReturnValue(
      buildPage({ selectedMemory: memory, sidePanelStatus: 'details' }),
    )
    render(<MemoriesPage />)

    expect(screen.getByRole('link', { name: 'Conversa' })).toHaveAttribute(
      'href',
      `${ROUTES.intelligence}?session=01J7T8AC91Z5K8M4JQ8C2D6FA3`,
    )
  })

  it('renders the edit form and saves the typed content', async () => {
    const user = userEvent.setup()
    useMemoriesPageMock.mockReturnValue(
      buildPage({ selectedMemory: memories[0] ?? null, sidePanelStatus: 'edit' }),
    )
    render(<MemoriesPage />)

    const field = screen.getByRole('textbox', { name: 'Conteúdo' })
    expect(field).toHaveFocus()
    await user.clear(field)
    await user.type(field, '  Agora entendo retornar valores.  ')
    await user.click(screen.getByRole('button', { name: 'Salvar memória' }))

    expect(handlers.handleSaveEdit).toHaveBeenCalledWith(
      'Agora entendo retornar valores.',
    )
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(handlers.handleCancelEdit).toHaveBeenCalledOnce()
  })

  it('does not save invalid content and explains why', async () => {
    const user = userEvent.setup()
    useMemoriesPageMock.mockReturnValue(
      buildPage({ selectedMemory: memories[0] ?? null, sidePanelStatus: 'edit' }),
    )
    render(<MemoriesPage />)

    await user.clear(screen.getByRole('textbox', { name: 'Conteúdo' }))
    await user.click(screen.getByRole('button', { name: 'Salvar memória' }))

    expect(handlers.handleSaveEdit).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('Escreva o conteúdo da memória.')
  })

  it('shows the pending save, a save failure and a conflict inside the open form', () => {
    useMemoriesPageMock.mockReturnValue(
      buildPage({
        selectedMemory: memories[0] ?? null,
        sidePanelStatus: 'edit',
        isSaving: true,
        saveError: 'Não foi possível salvar a memória. Tente novamente.',
        conflictContent: 'Conteúdo mais novo.',
      }),
    )
    render(<MemoriesPage />)

    expect(screen.getByRole('button', { name: 'Salvando…' })).toBeDisabled()
    const alerts = screen.getAllByRole('alert')
    expect(alerts.map((alert) => alert.textContent).join(' ')).toContain(
      'Conteúdo atual: Conteúdo mais novo.',
    )
    expect(alerts.map((alert) => alert.textContent).join(' ')).toContain(
      'Não foi possível salvar a memória. Tente novamente.',
    )
  })

  it('shows the removed notice with the way back to the Mentor', () => {
    useMemoriesPageMock.mockReturnValue(buildPage({ sidePanelStatus: 'removed' }))
    render(<MemoriesPage />)
    const notice = screen.getByRole('region', { name: 'Memória excluída' })

    expect(
      within(notice).getByRole('heading', { name: 'Memória excluída' }),
    ).toBeVisible()
    expect(
      within(notice).getByText(
        /Mensagens, anexos e resumos antigos não voltarão a criá-la/,
      ),
    ).toBeVisible()
    expect(
      within(notice).getByRole('link', { name: 'Voltar ao Mentor' }),
    ).toHaveAttribute('href', ROUTES.intelligence)
  })

  it.each([
    ['loading', 'Carregando memórias.'],
    ['not-found', 'Memória não encontrada'],
    ['error', 'Não foi possível carregar suas memórias'],
  ] as const)(
    'shows the %s state of a selected memory outside the list',
    (status, text) => {
      useMemoriesPageMock.mockReturnValue(buildPage({ sidePanelStatus: status }))
      render(<MemoriesPage />)
      const panel = screen.getByRole('complementary', { name: 'Painel da memória' })

      expect(within(panel).getByText(text)).toBeInTheDocument()
    },
  )

  it('confirms a deletion in a dialog with a destructive action', async () => {
    const user = userEvent.setup()
    useMemoriesPageMock.mockReturnValue(
      buildPage({
        selectedMemory: memories[0] ?? null,
        sidePanelStatus: 'details',
        isDeleteDialogOpen: true,
      }),
    )
    render(<MemoriesPage />)
    const dialog = screen.getByRole('alertdialog', { name: 'Excluir esta memória?' })

    expect(within(dialog).getByText('Confundo exibir e retornar valores.')).toBeVisible()
    await user.click(within(dialog).getByRole('button', { name: 'Excluir memória' }))
    await user.click(within(dialog).getByRole('button', { name: 'Manter memória' }))

    expect(handlers.handleConfirmDelete).toHaveBeenCalledOnce()
    expect(handlers.handleCancelDelete).toHaveBeenCalled()
  })

  it('disables the dialog while deleting and shows a deletion failure', () => {
    useMemoriesPageMock.mockReturnValue(
      buildPage({
        selectedMemory: memories[0] ?? null,
        sidePanelStatus: 'details',
        isDeleteDialogOpen: true,
        isDeleting: true,
        deleteError: 'Não foi possível excluir a memória. Tente novamente.',
      }),
    )
    render(<MemoriesPage />)
    const dialog = screen.getByRole('alertdialog', { name: 'Excluir esta memória?' })

    expect(within(dialog).getByRole('button', { name: 'Excluir memória' })).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Manter memória' })).toBeDisabled()
    expect(within(dialog).getByRole('alert')).toHaveTextContent(
      'Não foi possível excluir a memória. Tente novamente.',
    )
  })
})
