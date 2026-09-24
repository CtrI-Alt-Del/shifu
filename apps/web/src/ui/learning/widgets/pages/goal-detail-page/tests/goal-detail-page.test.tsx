import type { ComponentProps } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { GoalDetail } from '@/core/learning/goal-detail'

import { GoalDetailPage } from '..'
import { type GoalDetailPageController, useGoalDetailPage } from '../use-goal-detail-page'

type LinkMockProps = Omit<ComponentProps<'a'>, 'href'> & {
  params?: Record<string, string>
  to: string
}

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, to, ...props }: LinkMockProps) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
}))

vi.mock('@xyflow/react', () => ({
  Background: () => null,
  Controls: () => null,
  Handle: () => null,
  Position: { Bottom: 'bottom', Top: 'top' },
  ReactFlow: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('../use-goal-detail-page', () => ({ useGoalDetailPage: vi.fn() }))

const useGoalDetailPageMock = vi.mocked(useGoalDetailPage)

const goalId = '01SHF000000000000000000003'
const detail: GoalDetail = {
  goalId,
  title: 'Fundamentos de programação',
  description: 'Construa uma base sólida.',
  skills: [
    {
      skillExperienceId: '01SHF000000000000000000004',
      skillId: '01SHF000000000000000000005',
      name: 'Lógica',
      status: 'learning',
      progress: 60,
      inclusionReason: 'Base para programação',
    },
    {
      skillExperienceId: '01SHF000000000000000000006',
      skillId: '01SHF000000000000000000007',
      name: 'Algoritmos',
      status: 'completed',
      progress: null,
      inclusionReason: null,
    },
  ],
  relations: [
    {
      foundationSkillId: '01SHF000000000000000000005',
      skillId: '01SHF000000000000000000007',
    },
  ],
}

function makeController(
  overrides: Partial<GoalDetailPageController> = {},
): GoalDetailPageController {
  return {
    detail: null,
    state: 'loading',
    view: 'graph',
    isRetrying: false,
    handleRetry: vi.fn(),
    handleViewChange: vi.fn(),
    ...overrides,
  }
}

describe('GoalDetailPage', () => {
  afterEach(cleanup)

  beforeEach(() => useGoalDetailPageMock.mockReturnValue(makeController()))

  it('renders loading, private absence and retry states without stale data', () => {
    const { rerender } = render(<GoalDetailPage goalId={goalId} />)
    expect(screen.getByLabelText('Carregando objetivo')).toBeVisible()

    useGoalDetailPageMock.mockReturnValue(makeController({ state: 'not-found' }))
    rerender(<GoalDetailPage goalId={goalId} />)
    expect(screen.getByRole('heading', { name: 'Objetivo não encontrado' })).toBeVisible()

    useGoalDetailPageMock.mockReturnValue(
      makeController({ state: 'error', isRetrying: true }),
    )
    rerender(<GoalDetailPage goalId={goalId} />)
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })

  it('renders the semantic list, statuses and disabled future actions', () => {
    useGoalDetailPageMock.mockReturnValue(
      makeController({ detail, state: 'success', view: 'list' }),
    )
    render(<GoalDetailPage goalId={goalId} />)

    expect(screen.getByRole('heading', { name: detail.title })).toBeVisible()
    expect(screen.getByRole('list', { name: 'Habilidades do objetivo' })).toBeVisible()
    expect(screen.getByText('Em aprendizado')).toBeVisible()
    expect(screen.getByText('Concluída')).toBeVisible()
    expect(
      screen.getByRole('progressbar', { name: 'Progresso de Lógica' }),
    ).toHaveAttribute('aria-valuenow', '60')
    expect(
      screen.queryByRole('progressbar', { name: 'Progresso de Algoritmos' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remover objetivo' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Mais ações de Lógica' })).toBeDisabled()
  })

  it('renders the controlled tab state and delegates retry from the rendered control', () => {
    const handleRetry = vi.fn()
    useGoalDetailPageMock.mockReturnValue(
      makeController({ detail, state: 'success', view: 'graph' }),
    )
    const { rerender } = render(<GoalDetailPage goalId={goalId} />)
    expect(screen.getByRole('tab', { name: 'Grafo' })).toHaveAttribute(
      'data-state',
      'active',
    )
    expect(screen.getByRole('tab', { name: 'Lista' })).toHaveAttribute(
      'data-state',
      'inactive',
    )

    useGoalDetailPageMock.mockReturnValue(makeController({ state: 'error', handleRetry }))
    rerender(<GoalDetailPage goalId={goalId} />)
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(handleRetry).toHaveBeenCalledOnce()
  })
})
