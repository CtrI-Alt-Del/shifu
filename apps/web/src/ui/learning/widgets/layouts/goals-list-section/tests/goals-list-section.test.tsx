import type { Link } from '@tanstack/react-router'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useHomeGoalsQuery } from '@/ui/intelligence/hooks/use-home-goals-query'

import { GoalsListSection } from '..'

vi.mock('@/ui/intelligence/hooks/use-home-goals-query', () => ({
  useHomeGoalsQuery: vi.fn(),
}))

// ObjectiveCard renders a dynamic-route `Link` directly rather than the
// static-route `Anchor` wrapper (Anchor only resolves a fixed `RouteName`).
// `to`/`params` are typed against the real `Link` component's props so the
// mock fails to compile if that contract changes, per widget-testing-rules.md.
type RealLinkProps = React.ComponentProps<typeof Link>

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>()

  return {
    ...actual,
    Link: ({
      children,
      params,
      to,
      ...props
    }: Pick<RealLinkProps, 'children' | 'params' | 'to'>) => (
      <a
        href={String(to).replace(
          '$goalId',
          (params as { goalId?: string })?.goalId ?? '',
        )}
        {...props}
      >
        {typeof children === 'function' ? null : children}
      </a>
    ),
  }
})

const refetchGoalsMock = vi.fn()
const useHomeGoalsQueryMock = vi.mocked(useHomeGoalsQuery)

const firstGoal = {
  description: 'Construir uma base sólida para resolver problemas com clareza.',
  id: 'goal-1',
  skillCount: 3,
  title: 'Lógica de programação',
  updatedAt: '2026-01-05T00:00:00.000Z',
}

const secondGoal = {
  description: 'Criar scripts úteis para reduzir trabalho repetitivo.',
  id: 'goal-2',
  skillCount: 1,
  title: 'Automatizar tarefas com Python',
  updatedAt: '2026-01-04T00:00:00.000Z',
}

describe('GoalsListSection', () => {
  afterEach(cleanup)

  beforeEach(() => {
    refetchGoalsMock.mockReset()
    useHomeGoalsQueryMock.mockReturnValue({
      goals: [],
      goalsError: null,
      isLoadingGoals: false,
      refetchGoals: refetchGoalsMock,
    })
  })

  it('renders a distinct loading state while the objectives query is in flight', () => {
    useHomeGoalsQueryMock.mockReturnValue({
      goals: [],
      goalsError: null,
      isLoadingGoals: true,
      refetchGoals: refetchGoalsMock,
    })
    render(<GoalsListSection />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando seus objetivos...')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('renders a recoverable error state with a retry action', () => {
    useHomeGoalsQueryMock.mockReturnValue({
      goals: [],
      goalsError: new Error('network down'),
      isLoadingGoals: false,
      refetchGoals: refetchGoalsMock,
    })
    render(<GoalsListSection />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível carregar seus objetivos agora.',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(refetchGoalsMock).toHaveBeenCalledOnce()
  })

  it('renders an empty-state message when the account has no objectives', () => {
    render(<GoalsListSection />)

    expect(screen.getByText('Você ainda não tem objetivos.')).toBeVisible()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('renders every objective card with title, description and correct skill-count pluralization', () => {
    useHomeGoalsQueryMock.mockReturnValue({
      goals: [firstGoal, secondGoal],
      goalsError: null,
      isLoadingGoals: false,
      refetchGoals: refetchGoalsMock,
    })
    render(<GoalsListSection />)

    expect(screen.getByRole('heading', { name: 'Seus Objetivos' })).toBeVisible()
    expect(screen.getByText('2 objetivos')).toBeVisible()

    const firstCard = screen.getByRole('link', { name: /Lógica de programação/ })
    expect(firstCard).toHaveAttribute('href', '/learning/goals/goal-1')
    expect(firstCard).toHaveTextContent(
      'Construir uma base sólida para resolver problemas com clareza.',
    )
    expect(firstCard).toHaveTextContent('3 Habilidades')

    const secondCard = screen.getByRole('link', {
      name: /Automatizar tarefas com Python/,
    })
    expect(secondCard).toHaveAttribute('href', '/learning/goals/goal-2')
    expect(secondCard).toHaveTextContent('1 Habilidade')

    expect(screen.queryByText('Você ainda não tem objetivos.')).not.toBeInTheDocument()
  })

  it('shows the singular objective count label for exactly one objective', () => {
    useHomeGoalsQueryMock.mockReturnValue({
      goals: [firstGoal],
      goalsError: null,
      isLoadingGoals: false,
      refetchGoals: refetchGoalsMock,
    })
    render(<GoalsListSection />)

    expect(screen.getByText('1 objetivo')).toBeVisible()
  })
})
