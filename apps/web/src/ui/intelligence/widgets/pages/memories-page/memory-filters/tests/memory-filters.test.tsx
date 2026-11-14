import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { MemoryFilters, type MemoryFiltersProps } from '..'
import { useMemoryFilters } from '../use-memory-filters'

// Entrance motion and counters settle at once, so assertions see the final
// state; the shared components own their animated cases.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-memory-filters', () => ({
  MEMORY_SEARCH_MAX_LENGTH: 100,
  useMemoryFilters: vi.fn(),
}))

const useMemoryFiltersMock = vi.mocked(useMemoryFilters)
const handleQueryInputChangeMock = vi.fn()
const handleCategorySelectMock = vi.fn()
const onViewChangeMock = vi.fn()

function buildProps(overrides: Partial<MemoryFiltersProps> = {}): MemoryFiltersProps {
  return {
    query: '',
    category: null,
    view: 'list',
    totalCount: 8,
    onQueryChange: vi.fn(),
    onCategoryChange: vi.fn(),
    onViewChange: onViewChangeMock,
    ...overrides,
  }
}

describe('MemoryFilters', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMemoryFiltersMock.mockReturnValue({
      draftQuery: '',
      handleQueryInputChange: handleQueryInputChangeMock,
      handleCategorySelect: handleCategorySelectMock,
    })
  })
  afterEach(cleanup)

  it('renders the labelled search field and forwards typed text to its hook', async () => {
    const user = userEvent.setup()
    render(<MemoryFilters {...buildProps()} />)

    const search = screen.getByRole('searchbox', { name: 'Buscar memórias' })
    expect(search).toHaveAttribute('maxlength', '100')
    await user.type(search, 'a')

    expect(handleQueryInputChangeMock).toHaveBeenCalledWith('a')
  })

  it('shows the draft query returned by the hook', () => {
    useMemoryFiltersMock.mockReturnValue({
      draftQuery: 'funções',
      handleQueryInputChange: handleQueryInputChangeMock,
      handleCategorySelect: handleCategorySelectMock,
    })
    render(<MemoryFilters {...buildProps({ query: 'funções' })} />)

    expect(screen.getByRole('searchbox', { name: 'Buscar memórias' })).toHaveValue(
      'funções',
    )
  })

  it('renders pt-BR category chips with the total on "Todas" pressed by default', () => {
    render(<MemoryFilters {...buildProps()} />)

    expect(screen.getByRole('button', { name: 'Todas · 8' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    for (const label of [
      'Preferência de explicação',
      'Conhecimento declarado',
      'Interesse ou intenção',
      'Dificuldades recorrentes',
    ]) {
      expect(screen.getByRole('button', { name: label })).toHaveAttribute(
        'aria-pressed',
        'false',
      )
    }
    expect(screen.getByRole('button', { name: 'Categoria: Todas' })).toBeVisible()
  })

  it('marks only the active category chip as pressed and drops the unknown total', () => {
    render(
      <MemoryFilters
        {...buildProps({ category: 'recurring_difficulty', totalCount: null })}
      />,
    )

    expect(screen.getByRole('button', { name: 'Todas' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(
      screen.getByRole('button', { name: 'Dificuldades recorrentes' }),
    ).toHaveAttribute('aria-pressed', 'true')
    expect(
      screen.getByRole('button', { name: 'Categoria: Dificuldades recorrentes' }),
    ).toBeVisible()
  })

  it('delegates chip selection with the canonical category value', async () => {
    const user = userEvent.setup()
    render(<MemoryFilters {...buildProps({ category: 'declared_knowledge' })} />)

    await user.click(screen.getByRole('button', { name: 'Interesse ou intenção' }))
    await user.click(screen.getByRole('button', { name: 'Todas · 8' }))

    expect(handleCategorySelectMock).toHaveBeenNthCalledWith(1, 'interest_or_intention')
    expect(handleCategorySelectMock).toHaveBeenNthCalledWith(2, 'all')
  })

  it('offers a single-choice mobile menu with the selected category checked', async () => {
    const user = userEvent.setup()
    render(<MemoryFilters {...buildProps({ category: 'declared_knowledge' })} />)

    await user.click(
      screen.getByRole('button', { name: 'Categoria: Conhecimento declarado' }),
    )

    expect(
      screen.getByRole('menuitemradio', { name: 'Conhecimento declarado' }),
    ).toBeChecked()
    expect(screen.getByRole('menuitemradio', { name: 'Todas' })).not.toBeChecked()
    await user.click(
      screen.getByRole('menuitemradio', { name: 'Preferência de explicação' }),
    )

    expect(handleCategorySelectMock).toHaveBeenCalledWith('explanation_preference')
  })

  it('selects "Todas" from the mobile menu', async () => {
    const user = userEvent.setup()
    render(<MemoryFilters {...buildProps({ category: 'declared_knowledge' })} />)

    await user.click(
      screen.getByRole('button', { name: 'Categoria: Conhecimento declarado' }),
    )
    await user.click(screen.getByRole('menuitemradio', { name: 'Todas' }))

    expect(handleCategorySelectMock).toHaveBeenCalledWith('all')
  })

  it('switches the view with the Lista and Mapa tabs', async () => {
    const user = userEvent.setup()
    render(<MemoryFilters {...buildProps({ view: 'list' })} />)

    expect(screen.getByRole('tab', { name: 'Lista' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    await user.click(screen.getByRole('tab', { name: 'Mapa' }))

    expect(onViewChangeMock).toHaveBeenCalledWith('map')
  })

  it('marks the map tab as selected for the map view', () => {
    render(<MemoryFilters {...buildProps({ view: 'map' })} />)

    expect(screen.getByRole('tab', { name: 'Mapa' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })

  it('offers a mobile button that opens the map from the list view', async () => {
    const user = userEvent.setup()
    render(<MemoryFilters {...buildProps({ view: 'list' })} />)

    await user.click(screen.getByRole('button', { name: 'Ver Mapa' }))

    expect(onViewChangeMock).toHaveBeenCalledWith('map')
    expect(screen.queryByRole('button', { name: 'Ver Lista' })).not.toBeInTheDocument()
  })

  it('offers a mobile button that returns to the list from the map view', async () => {
    const user = userEvent.setup()
    render(<MemoryFilters {...buildProps({ view: 'map' })} />)

    await user.click(screen.getByRole('button', { name: 'Ver Lista' }))

    expect(onViewChangeMock).toHaveBeenCalledWith('list')
    expect(screen.queryByRole('button', { name: 'Ver Mapa' })).not.toBeInTheDocument()
  })
})
