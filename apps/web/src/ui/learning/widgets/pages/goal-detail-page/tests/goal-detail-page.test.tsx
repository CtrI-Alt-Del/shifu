import type { ComponentProps } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
    isConfirmDialogOpen: false,
    isDeletingGoal: false,
    deleteGoalError: null,
    selectedSkill: null,
    isRemovingSkill: false,
    removeSkillError: null,
    skillRemovalTriggerRef: { current: null },
    handleRetry: vi.fn(),
    handleViewChange: vi.fn(),
    handleOpenConfirmDialog: vi.fn(),
    handleCancelRemoval: vi.fn(),
    handleConfirmRemoval: vi.fn(),
    handleOpenSkillRemoval: vi.fn(),
    handleCancelSkillRemoval: vi.fn(),
    handleConfirmSkillRemoval: vi.fn(async () => {}),
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

  it('renders the semantic list, statuses and delegates skill removal', async () => {
    const user = userEvent.setup()
    const handleOpenSkillRemoval = vi.fn()
    useGoalDetailPageMock.mockReturnValue(
      makeController({ detail, state: 'success', view: 'list', handleOpenSkillRemoval }),
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
    expect(screen.getByRole('button', { name: 'Remover objetivo' })).toBeEnabled()
    await user.click(screen.getByRole('button', { name: 'Mais ações de Lógica' }))
    await user.click(screen.getByRole('menuitem', { name: 'Remover habilidade' }))
    expect(handleOpenSkillRemoval).toHaveBeenCalledWith(
      detail.skills[0],
      expect.any(HTMLButtonElement),
    )
  })

  it('keeps the skill dialog open with loss scope and recoverable error', () => {
    useGoalDetailPageMock.mockReturnValue(
      makeController({
        detail,
        state: 'success',
        view: 'list',
        selectedSkill: detail.skills[0],
        removeSkillError: 'Não foi possível remover a Habilidade. Tente novamente.',
      }),
    )
    render(<GoalDetailPage goalId={goalId} />)

    expect(screen.getByRole('heading', { name: 'Remover Habilidade?' })).toBeVisible()
    expect(screen.getByText('Tentativas, avaliações e resumo final')).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent('Tente novamente')
  })

  it('opens the removal confirmation dialog from the header trigger', () => {
    const handleOpenConfirmDialog = vi.fn()
    useGoalDetailPageMock.mockReturnValue(
      makeController({
        detail,
        state: 'success',
        view: 'list',
        handleOpenConfirmDialog,
      }),
    )
    render(<GoalDetailPage goalId={goalId} />)

    fireEvent.click(screen.getByRole('button', { name: 'Remover objetivo' }))
    expect(handleOpenConfirmDialog).toHaveBeenCalledOnce()
  })

  it('renders the confirmation dialog with the objective name when open', () => {
    useGoalDetailPageMock.mockReturnValue(
      makeController({
        detail,
        state: 'success',
        view: 'list',
        isConfirmDialogOpen: true,
      }),
    )
    render(<GoalDetailPage goalId={goalId} />)

    expect(screen.getByRole('heading', { name: 'Remover este objetivo?' })).toBeVisible()
    expect(screen.getAllByText(detail.title)).toHaveLength(2)
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
