import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, it, expect, vi } from 'vitest'
import { SkillCatalogView } from '../index'

describe('SkillCatalogView', () => {
  afterEach(cleanup)

  const mockSkills = [
    {
      id: 's1',
      name: 'React',
      description: 'Learn React fundamentals',
      alreadyInGoal: false,
      skillExperienceId: null,
      foundations: [{ skillId: 'f1', name: 'JavaScript', status: 'present' as const }],
    },
    {
      id: 's2',
      name: 'TypeScript',
      description: 'Learn TypeScript',
      alreadyInGoal: true,
      skillExperienceId: 'exp123',
      foundations: [],
    },
    {
      id: 's3',
      name: 'Node.js',
      description: 'Backend development',
      alreadyInGoal: false,
      skillExperienceId: null,
      foundations: [
        { skillId: 'f2', name: 'JavaScript', status: 'missing' as const },
        { skillId: 'f3', name: 'Express', status: 'missing' as const },
      ],
    },
  ]

  it('renders skills list', () => {
    render(<SkillCatalogView skills={mockSkills} onSkillSelect={vi.fn()} />)

    expect(screen.getByText('React')).toBeInTheDocument()
    expect(screen.getByText('TypeScript')).toBeInTheDocument()
    expect(screen.getByText('Node.js')).toBeInTheDocument()
  })

  it('shows "Adicionar" button for skills not in goal', () => {
    render(<SkillCatalogView skills={mockSkills} onSkillSelect={vi.fn()} />)

    const addButtons = screen.getAllByRole('button', { name: /Adicionar/ })
    expect(addButtons).toHaveLength(2)
  })

  it('shows "Adicionado" status for skills already in goal', () => {
    render(<SkillCatalogView skills={mockSkills} onSkillSelect={vi.fn()} />)

    expect(screen.getByText('Adicionado')).toBeInTheDocument()
  })

  it('calls onSkillSelect when add button clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<SkillCatalogView skills={mockSkills} onSkillSelect={onSelect} />)

    const addButtons = screen.getAllByRole('button', { name: /Adicionar/ })
    await user.click(addButtons[0])

    expect(onSelect).toHaveBeenCalledWith(mockSkills[0])
  })

  it('displays single foundation inline', () => {
    render(<SkillCatalogView skills={[mockSkills[0]]} onSkillSelect={vi.fn()} />)

    expect(screen.getByText(/Base sugerida:/)).toBeInTheDocument()
    expect(screen.getByText('JavaScript')).toBeInTheDocument()
  })

  it('shows expand/collapse toggle for multiple foundations', () => {
    render(<SkillCatalogView skills={[mockSkills[2]]} onSkillSelect={vi.fn()} />)

    expect(screen.getByText(/Ver bases \(2\)/)).toBeInTheDocument()
  })

  it('expands foundations when toggle clicked', async () => {
    const user = userEvent.setup()

    render(<SkillCatalogView skills={[mockSkills[2]]} onSkillSelect={vi.fn()} />)

    const toggleButton = screen.getByRole('button', { name: /Ver bases/ })
    await user.click(toggleButton)

    expect(screen.getByText('JavaScript')).toBeInTheDocument()
    expect(screen.getByText('Express')).toBeInTheDocument()
    expect(screen.getByText(/Ocultar bases/)).toBeInTheDocument()
  })

  it('collapses foundations when toggle clicked again', async () => {
    const user = userEvent.setup()

    render(<SkillCatalogView skills={[mockSkills[2]]} onSkillSelect={vi.fn()} />)

    const toggleButton = screen.getByRole('button', { name: /Ver bases/ })
    await user.click(toggleButton)

    expect(screen.getByText('Express')).toBeInTheDocument()

    await user.click(toggleButton)

    expect(screen.queryByText('Express')).not.toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(<SkillCatalogView skills={[]} isLoading={true} onSkillSelect={vi.fn()} />)

    expect(screen.getByText(/Carregando habilidades/)).toBeInTheDocument()
  })

  it('shows error message', () => {
    render(
      <SkillCatalogView
        skills={[]}
        error='Failed to load skills'
        onSkillSelect={vi.fn()}
      />,
    )

    expect(screen.getByText('Failed to load skills')).toBeInTheDocument()
  })

  it('shows empty state when no skills', () => {
    render(<SkillCatalogView skills={[]} onSkillSelect={vi.fn()} />)

    expect(screen.getByText(/Nenhuma habilidade encontrada/)).toBeInTheDocument()
  })

  it('shows load more button when hasMore is true', () => {
    render(
      <SkillCatalogView
        skills={mockSkills}
        onSkillSelect={vi.fn()}
        hasMore={true}
        onLoadMore={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /Carregar mais/ })).toBeInTheDocument()
  })

  it('calls onLoadMore when load more clicked', async () => {
    const user = userEvent.setup()
    const onLoadMore = vi.fn()

    render(
      <SkillCatalogView
        skills={mockSkills}
        onSkillSelect={vi.fn()}
        hasMore={true}
        onLoadMore={onLoadMore}
      />,
    )

    const loadMoreButton = screen.getByRole('button', { name: /Carregar mais/ })
    await user.click(loadMoreButton)

    expect(onLoadMore).toHaveBeenCalled()
  })

  it('disables load more button when loading', () => {
    render(
      <SkillCatalogView
        skills={mockSkills}
        isLoading={true}
        onSkillSelect={vi.fn()}
        hasMore={true}
        onLoadMore={vi.fn()}
      />,
    )

    const loadMoreButton = screen.getByRole('button', { name: /Carregando/ })
    expect(loadMoreButton).toBeDisabled()
  })
})
