import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { createElement, type PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import { RestError } from '@/core/errors/rest-error'
import { LearnerMemoryFaker } from '@/core/intelligence/fakers/learner-memory-faker'
import type { LearnerMemory } from '@/core/intelligence/learner-memory'

import { useMemoriesPage } from '../use-memories-page'

type SearchValue = Record<string, unknown>

const mocks = vi.hoisted(() => {
  const store = {
    value: {} as Record<string, unknown>,
    listeners: new Set<() => void>(),
  }
  return {
    store,
    navigate: vi.fn(),
    service: {
      listLearnerMemories: vi.fn(),
      getLearnerMemory: vi.fn(),
      editLearnerMemory: vi.fn(),
      removeLearnerMemory: vi.fn(),
    },
  }
})

vi.mock('@tanstack/react-router', async () => {
  const { useSyncExternalStore } = await import('react')
  return {
    useNavigate: () => mocks.navigate,
    useRouteContext: () => ({ email: 'learner@example.test', displayName: 'Aprendiz' }),
    useSearch: () =>
      useSyncExternalStore(
        (listener) => {
          mocks.store.listeners.add(listener)
          return () => mocks.store.listeners.delete(listener)
        },
        () => mocks.store.value,
      ),
  }
})
vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    validator: (validate: (data: unknown) => unknown) => ({
      handler:
        (handler: (context: { data: unknown }) => Promise<unknown>) =>
        async (context: { data: unknown }) =>
          handler({ data: validate(context.data) }),
    }),
  }),
}))
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://shifu.test/intelligence/memories'),
}))
vi.mock('@/provision/realtime/mentor-response-stream-server-provider', () => ({
  getMentorScopedService: async () => ({
    accessToken: 'access-token',
    service: mocks.service,
  }),
}))

const FIRST_ID = '01J7T8AC91Z5K8M4JQ8C2D6F01'
const SECOND_ID = '01J7T8AC91Z5K8M4JQ8C2D6F02'
const OUTSIDE_ID = '01J7T8AC91Z5K8M4JQ8C2D6F09'

const first = LearnerMemoryFaker.fake({
  id: FIRST_ID,
  content: 'Prefiro exemplos curtos.',
  version: 1,
})
const second = LearnerMemoryFaker.fake({ id: SECOND_ID, content: 'Sei Python.' })

function setSearch(search: SearchValue) {
  mocks.store.value = { view: 'list', ...search }
  for (const listener of mocks.store.listeners) listener()
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const wrapper = ({ children }: PropsWithChildren) =>
    createElement(QueryClientProvider, { client }, children)
  return { client, ...renderHook(() => useMemoriesPage(), { wrapper }) }
}

async function renderLoadedPage(selectedMemoryId?: string) {
  setSearch(selectedMemoryId ? { memory: selectedMemoryId } : {})
  const rendered = renderPage()
  await waitFor(() => expect(rendered.result.current.listStatus).toBe('ready'))
  return rendered
}

describe('useMemoriesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.navigate.mockImplementation(({ search }: { search: SearchValue }) => {
      setSearch(search)
    })
    mocks.service.listLearnerMemories.mockResolvedValue([first, second])
    mocks.service.getLearnerMemory.mockResolvedValue(
      LearnerMemoryFaker.fake({ id: OUTSIDE_ID }),
    )
    setSearch({})
  })
  afterEach(cleanup)

  it('loads the memories for the URL filters and exposes them', async () => {
    setSearch({ q: 'python', category: 'declared_knowledge', view: 'map' })
    const { result } = renderPage()

    expect(result.current.listStatus).toBe('loading')
    expect(result.current.totalCount).toBeNull()
    await waitFor(() => expect(result.current.listStatus).toBe('ready'))

    expect(mocks.service.listLearnerMemories).toHaveBeenCalledWith('access-token', {
      q: 'python',
      category: 'declared_knowledge',
    })
    expect(result.current.memories).toEqual([first, second])
    expect(result.current.query).toBe('python')
    expect(result.current.category).toBe('declared_knowledge')
    expect(result.current.view).toBe('map')
    expect(result.current.totalCount).toBeNull()
    expect(result.current.sidePanelStatus).toBe('none')
  })

  it('counts every memory when no category filter is active', async () => {
    const { result } = await renderLoadedPage()

    expect(mocks.service.listLearnerMemories).toHaveBeenCalledWith('access-token', {
      q: undefined,
      category: undefined,
    })
    expect(result.current.totalCount).toBe(2)
    expect(result.current.query).toBe('')
    expect(result.current.category).toBeNull()
  })

  it('reports an empty account and an empty filtered result differently', async () => {
    mocks.service.listLearnerMemories.mockResolvedValue([])
    const empty = await (async () => {
      setSearch({})
      const rendered = renderPage()
      await waitFor(() => expect(rendered.result.current.listStatus).toBe('empty'))
      return rendered
    })()
    empty.unmount()

    setSearch({ q: 'nada' })
    const filtered = renderPage()
    await waitFor(() => expect(filtered.result.current.listStatus).toBe('empty-filtered'))
  })

  it('reports a failed read and recovers when it is retried', async () => {
    mocks.service.listLearnerMemories.mockRejectedValueOnce(new RestError('falha', 500))
    setSearch({})
    const { result } = renderPage()

    await waitFor(() => expect(result.current.listStatus).toBe('error'))
    act(() => result.current.handleRetry())

    await waitFor(() => expect(result.current.listStatus).toBe('ready'))
    expect(mocks.service.listLearnerMemories).toHaveBeenCalledTimes(2)
  })

  it('writes each filter change to the URL with replace, keeps the other values and the scroll', async () => {
    setSearch({
      q: 'python',
      category: 'declared_knowledge',
      view: 'list',
      memory: FIRST_ID,
    })
    const { result } = renderPage()
    await waitFor(() => expect(result.current.listStatus).toBe('ready'))

    act(() => result.current.handleQueryChange('node'))
    expect(mocks.navigate).toHaveBeenLastCalledWith({
      to: ROUTES.intelligenceMemories,
      search: {
        q: 'node',
        category: 'declared_knowledge',
        view: 'list',
        memory: FIRST_ID,
      },
      replace: true,
      resetScroll: false,
    })

    act(() => result.current.handleCategoryChange(null))
    expect(mocks.navigate.mock.lastCall?.[0].search).toMatchObject({
      category: undefined,
      q: 'node',
    })

    act(() => result.current.handleViewChange('map'))
    expect(mocks.navigate.mock.lastCall?.[0].search).toMatchObject({ view: 'map' })

    act(() => result.current.handleQueryChange(''))
    expect(mocks.navigate.mock.lastCall?.[0].search).toMatchObject({ q: undefined })
  })

  it('clears the search and the category together', async () => {
    setSearch({ q: 'python', category: 'declared_knowledge' })
    const { result } = renderPage()
    await waitFor(() => expect(result.current.listStatus).toBe('ready'))

    act(() => result.current.handleClearFilters())

    expect(mocks.navigate.mock.lastCall?.[0].search).toMatchObject({
      q: undefined,
      category: undefined,
    })
  })

  it('selects a listed memory without an extra request and closes its details', async () => {
    const { result } = await renderLoadedPage(FIRST_ID)

    expect(result.current.selectedMemory).toEqual(first)
    expect(result.current.sidePanelStatus).toBe('details')
    expect(mocks.service.getLearnerMemory).not.toHaveBeenCalled()

    act(() => result.current.handleSelectMemory(SECOND_ID))
    await waitFor(() => expect(result.current.selectedMemory).toEqual(second))

    act(() => result.current.handleCloseDetails())
    await waitFor(() => expect(result.current.sidePanelStatus).toBe('none'))
    expect(mocks.navigate.mock.lastCall?.[0].search).toMatchObject({ memory: undefined })
  })

  it('reads a selected memory that is outside the filtered list', async () => {
    const { result } = await renderLoadedPage(OUTSIDE_ID)

    await waitFor(() => expect(result.current.sidePanelStatus).toBe('details'))
    expect(mocks.service.getLearnerMemory).toHaveBeenCalledWith(
      'access-token',
      OUTSIDE_ID,
    )
    expect(result.current.selectedMemory?.id).toBe(OUTSIDE_ID)
  })

  it('reports a selected memory that does not exist', async () => {
    mocks.service.getLearnerMemory.mockRejectedValue(new RestError('não existe', 404))
    const { result } = await renderLoadedPage(OUTSIDE_ID)

    await waitFor(() => expect(result.current.sidePanelStatus).toBe('not-found'))
    expect(result.current.selectedMemory).toBeNull()
  })

  it('reports a failed read of the selected memory and retries it', async () => {
    mocks.service.getLearnerMemory.mockRejectedValueOnce(new RestError('falha', 500))
    const { result } = await renderLoadedPage(OUTSIDE_ID)

    await waitFor(() => expect(result.current.sidePanelStatus).toBe('error'))
    act(() => result.current.handleRetry())

    await waitFor(() => expect(result.current.sidePanelStatus).toBe('details'))
  })

  it('shows the loading state while the selected memory is read', async () => {
    let resolveMemory: (memory: LearnerMemory) => void = () => undefined
    mocks.service.getLearnerMemory.mockReturnValue(
      new Promise<LearnerMemory>((resolve) => {
        resolveMemory = resolve
      }),
    )
    const { result } = await renderLoadedPage(OUTSIDE_ID)

    await waitFor(() => expect(result.current.isLoadingSelectedMemory).toBe(true))
    expect(result.current.sidePanelStatus).toBe('loading')
    await act(async () => resolveMemory(LearnerMemoryFaker.fake({ id: OUTSIDE_ID })))
    await waitFor(() => expect(result.current.sidePanelStatus).toBe('details'))
  })

  it('opens and cancels the edit form', async () => {
    const { result } = await renderLoadedPage(FIRST_ID)

    act(() => result.current.handleStartEdit())
    expect(result.current.sidePanelStatus).toBe('edit')
    act(() => result.current.handleCancelEdit())

    expect(result.current.sidePanelStatus).toBe('details')
  })

  it('ignores edit and delete requests without a selected memory', async () => {
    const { result } = await renderLoadedPage()

    act(() => result.current.handleStartEdit())
    act(() => result.current.handleRequestDelete())
    await act(async () => result.current.handleSaveEdit('texto'))

    expect(result.current.sidePanelStatus).toBe('none')
    expect(result.current.isDeleteDialogOpen).toBe(false)
    expect(mocks.service.editLearnerMemory).not.toHaveBeenCalled()
  })

  it('saves an edit with the expected version and refreshes the memory', async () => {
    const updated = { ...first, content: 'Prefiro exemplos longos.', version: 2 }
    mocks.service.editLearnerMemory.mockResolvedValue(updated)
    const { result } = await renderLoadedPage(FIRST_ID)
    mocks.service.listLearnerMemories.mockResolvedValue([updated, second])
    act(() => result.current.handleStartEdit())

    await act(async () => result.current.handleSaveEdit('Prefiro exemplos longos.'))

    expect(mocks.service.editLearnerMemory).toHaveBeenCalledWith(
      'access-token',
      FIRST_ID,
      {
        content: 'Prefiro exemplos longos.',
        expectedVersion: 1,
      },
    )
    await waitFor(() =>
      expect(result.current.selectedMemory?.content).toBe(updated.content),
    )
    expect(result.current.sidePanelStatus).toBe('details')
    expect(result.current.saveError).toBeNull()
  })

  it('keeps the form open and shows the current content after a stale save', async () => {
    mocks.service.editLearnerMemory.mockRejectedValue(new RestError('conflito', 409))
    const { result } = await renderLoadedPage(FIRST_ID)
    const current = { ...first, content: 'Texto mais novo.', version: 2 }
    mocks.service.listLearnerMemories.mockResolvedValue([current, second])
    act(() => result.current.handleStartEdit())

    await act(async () => result.current.handleSaveEdit('Meu texto.'))

    await waitFor(() => expect(result.current.conflictContent).toBe('Texto mais novo.'))
    expect(result.current.sidePanelStatus).toBe('edit')
    mocks.service.editLearnerMemory.mockResolvedValue({
      ...current,
      content: 'Meu texto.',
      version: 3,
    })
    await act(async () => result.current.handleSaveEdit('Meu texto.'))

    expect(mocks.service.editLearnerMemory).toHaveBeenLastCalledWith(
      'access-token',
      FIRST_ID,
      { content: 'Meu texto.', expectedVersion: 2 },
    )
    await waitFor(() => expect(result.current.conflictContent).toBeNull())
  })

  it('shows a save error for content the server rejects', async () => {
    mocks.service.editLearnerMemory.mockRejectedValue(new RestError('inválido', 422))
    const { result } = await renderLoadedPage(FIRST_ID)
    act(() => result.current.handleStartEdit())

    await act(async () => result.current.handleSaveEdit('Texto.'))

    expect(result.current.saveError).toBe(
      'O conteúdo da memória deve ter entre 1 e 280 caracteres.',
    )
    expect(result.current.sidePanelStatus).toBe('edit')
  })

  it('shows a generic save error when the request fails', async () => {
    mocks.service.editLearnerMemory.mockRejectedValue(new RestError('falha', 500))
    const { result } = await renderLoadedPage(FIRST_ID)
    act(() => result.current.handleStartEdit())

    await act(async () => result.current.handleSaveEdit('Texto.'))

    expect(result.current.saveError).toBe(
      'Não foi possível salvar a memória. Tente novamente.',
    )
    expect(result.current.isSaving).toBe(false)
  })

  it('treats an edit of a memory removed elsewhere as a removal', async () => {
    mocks.service.editLearnerMemory.mockRejectedValue(new RestError('não existe', 404))
    const { result } = await renderLoadedPage(FIRST_ID)
    mocks.service.listLearnerMemories.mockResolvedValue([second])
    act(() => result.current.handleStartEdit())

    await act(async () => result.current.handleSaveEdit('Texto.'))

    await waitFor(() => expect(result.current.sidePanelStatus).toBe('removed'))
    expect(mocks.navigate.mock.lastCall?.[0].search).toMatchObject({ memory: undefined })
  })

  it('asks for confirmation before deleting and lets the learner back out', async () => {
    const { result } = await renderLoadedPage(FIRST_ID)

    act(() => result.current.handleRequestDelete())
    expect(result.current.isDeleteDialogOpen).toBe(true)
    act(() => result.current.handleCancelDelete())

    expect(result.current.isDeleteDialogOpen).toBe(false)
    expect(mocks.service.removeLearnerMemory).not.toHaveBeenCalled()
  })

  it('deletes the selected memory, shows the removed notice and refreshes the list', async () => {
    mocks.service.removeLearnerMemory.mockResolvedValue(undefined)
    const { result } = await renderLoadedPage(FIRST_ID)
    mocks.service.listLearnerMemories.mockResolvedValue([second])
    act(() => result.current.handleRequestDelete())

    await act(async () => result.current.handleConfirmDelete())

    expect(mocks.service.removeLearnerMemory).toHaveBeenCalledWith(
      'access-token',
      FIRST_ID,
    )
    await waitFor(() => expect(result.current.sidePanelStatus).toBe('removed'))
    expect(result.current.isDeleteDialogOpen).toBe(false)
    await waitFor(() => expect(result.current.memories).toEqual([second]))
    expect(result.current.selectedMemory).toBeNull()
  })

  it('hides the removed notice when another memory is selected', async () => {
    mocks.service.removeLearnerMemory.mockResolvedValue(undefined)
    const { result } = await renderLoadedPage(FIRST_ID)
    mocks.service.listLearnerMemories.mockResolvedValue([second])
    act(() => result.current.handleRequestDelete())
    await act(async () => result.current.handleConfirmDelete())
    await waitFor(() => expect(result.current.sidePanelStatus).toBe('removed'))

    act(() => result.current.handleSelectMemory(SECOND_ID))

    await waitFor(() => expect(result.current.sidePanelStatus).toBe('details'))
  })

  it('keeps the dialog open with an error when the deletion fails', async () => {
    mocks.service.removeLearnerMemory.mockRejectedValue(new RestError('falha', 500))
    const { result } = await renderLoadedPage(FIRST_ID)
    act(() => result.current.handleRequestDelete())

    await act(async () => result.current.handleConfirmDelete())

    expect(result.current.deleteError).toBe(
      'Não foi possível excluir a memória. Tente novamente.',
    )
    expect(result.current.isDeleteDialogOpen).toBe(true)
    expect(result.current.sidePanelStatus).toBe('details')
    act(() => result.current.handleCancelDelete())
    expect(result.current.deleteError).toBeNull()
  })

  it('ignores a confirmation when no deletion was requested', async () => {
    const { result } = await renderLoadedPage(FIRST_ID)

    await act(async () => result.current.handleConfirmDelete())

    expect(mocks.service.removeLearnerMemory).not.toHaveBeenCalled()
  })

  it('shows the loading state, not the previous results, while a new filter is read', async () => {
    const { result } = await renderLoadedPage(FIRST_ID)
    expect(result.current.totalCount).toBe(2)
    let resolveFiltered: (memories: LearnerMemory[]) => void = () => undefined
    mocks.service.listLearnerMemories.mockReturnValue(
      new Promise<LearnerMemory[]>((resolve) => {
        resolveFiltered = resolve
      }),
    )

    act(() => setSearch({ q: 'sei', memory: FIRST_ID }))

    await waitFor(() => expect(result.current.listStatus).toBe('loading'))
    expect(result.current.memories).toEqual([])
    expect(result.current.totalCount).toBeNull()
    expect(result.current.selectedMemory).toBeNull()
    expect(result.current.sidePanelStatus).toBe('loading')
    await act(async () => resolveFiltered([second]))
    await waitFor(() => expect(result.current.listStatus).toBe('ready'))
    expect(result.current.memories).toEqual([second])
  })
})
