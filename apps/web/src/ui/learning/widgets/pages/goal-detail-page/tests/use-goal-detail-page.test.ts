import { createElement, type ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { GoalDetail } from '@/core/learning/goal-detail'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useDeleteGoalAction } from '../use-delete-goal-action'
import { useGoalDetailPage } from '../use-goal-detail-page'
import { useGoalDetailQuery } from '../use-goal-detail-query'

vi.mock('../use-goal-detail-query', () => ({ useGoalDetailQuery: vi.fn() }))
vi.mock('../use-delete-goal-action', () => ({ useDeleteGoalAction: vi.fn() }))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({ useNavigation: vi.fn() }))

const useGoalDetailQueryMock = vi.mocked(useGoalDetailQuery)
const useDeleteGoalActionMock = vi.mocked(useDeleteGoalAction)
const useNavigationMock = vi.mocked(useNavigation)
const navigateToMock = vi.fn()
const refetchGoalDetailMock = vi.fn()
const deleteGoalMock = vi.fn()
const goalId = '01SHF000000000000000000003'
const detail: GoalDetail = {
  goalId,
  title: 'Fundamentos',
  description: 'Descrição',
  skills: [],
  relations: [],
}

function mockQuery(overrides: Partial<ReturnType<typeof useGoalDetailQuery>> = {}) {
  useGoalDetailQueryMock.mockReturnValue({
    goalDetail: null,
    goalDetailError: null,
    isLoadingGoalDetail: false,
    isFetchingGoalDetail: false,
    refetchGoalDetail: refetchGoalDetailMock,
    ...overrides,
  })
}

function createWrapper() {
  const queryClient = new QueryClient()
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useGoalDetailPage', () => {
  beforeEach(() => {
    navigateToMock.mockReset()
    refetchGoalDetailMock.mockReset()
    deleteGoalMock.mockReset()
    useGoalDetailQueryMock.mockReset()
    useDeleteGoalActionMock.mockReset()
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock,
      navigateToGoalDetail: vi.fn(),
      navigateToActivity: vi.fn(),
      navigateToPlanner: vi.fn(),
    })
    useDeleteGoalActionMock.mockReturnValue({
      deleteGoal: deleteGoalMock,
      isDeletingGoal: false,
      deleteGoalError: null,
      resetDeleteGoal: vi.fn(),
    })
    mockQuery()
  })

  it('starts in graph and classifies loading, empty, absence and recoverable states', () => {
    mockQuery({ isLoadingGoalDetail: true })
    const { result, rerender } = renderHook(
      ({ id }) => useGoalDetailPage({ goalId: id }),
      { initialProps: { id: goalId }, wrapper: createWrapper() },
    )
    expect(result.current.state).toBe('loading')
    expect(result.current.view).toBe('graph')

    mockQuery({ goalDetail: detail })
    rerender({ id: goalId })
    expect(result.current.state).toBe('empty')

    mockQuery({ goalDetailError: new RestError('Not found.', 404) })
    rerender({ id: goalId })
    expect(result.current.state).toBe('not-found')

    mockQuery({ goalDetailError: new RestError('Unavailable.', 503) })
    rerender({ id: goalId })
    expect(result.current.state).toBe('error')
  })

  it('changes only valid views and delegates explicit retry', () => {
    mockQuery({
      goalDetail: {
        ...detail,
        skills: [
          {
            skillExperienceId: 'a',
            skillId: 'b',
            name: 'Lógica',
            status: 'not-started',
            progress: null,
            inclusionReason: null,
          },
        ],
      },
    })
    const { result } = renderHook(() => useGoalDetailPage({ goalId }), {
      wrapper: createWrapper(),
    })
    act(() => result.current.handleViewChange('list'))
    expect(result.current.view).toBe('list')
    act(() => result.current.handleViewChange('invalid'))
    expect(result.current.view).toBe('list')
    result.current.handleRetry()
    expect(refetchGoalDetailMock).toHaveBeenCalledOnce()
  })

  it('redirects rejected sessions without classifying them as recoverable', async () => {
    mockQuery({
      goalDetailError: new AuthError('authentication-rejected', 'Expired.', {
        statusCode: 401,
      }),
    })
    const { result } = renderHook(() => useGoalDetailPage({ goalId }), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('login'))
    expect(result.current.state).toBe('error')
  })

  it('toggles the removal confirmation dialog open and closed', () => {
    mockQuery({ goalDetail: detail })
    const { result } = renderHook(() => useGoalDetailPage({ goalId }), {
      wrapper: createWrapper(),
    })

    expect(result.current.isConfirmDialogOpen).toBe(false)
    act(() => result.current.handleOpenConfirmDialog())
    expect(result.current.isConfirmDialogOpen).toBe(true)
    act(() => result.current.handleCancelRemoval())
    expect(result.current.isConfirmDialogOpen).toBe(false)
  })

  it('invalidates the home-goals query then navigates home after a successful removal', async () => {
    mockQuery({ goalDetail: detail })
    let onSuccess: (() => void | Promise<void>) | undefined
    deleteGoalMock.mockImplementation(
      (_input: unknown, options: { onSuccess?: () => void | Promise<void> }) => {
        onSuccess = options.onSuccess
      },
    )
    const { result } = renderHook(() => useGoalDetailPage({ goalId }), {
      wrapper: createWrapper(),
    })

    act(() => result.current.handleConfirmRemoval())
    expect(deleteGoalMock).toHaveBeenCalledOnce()

    expect(navigateToMock).not.toHaveBeenCalled()
    await act(async () => {
      await onSuccess?.()
    })
    expect(navigateToMock).toHaveBeenCalledWith('root')
  })

  it('surfaces the delete error while keeping the dialog open', () => {
    mockQuery({ goalDetail: detail })
    useDeleteGoalActionMock.mockReturnValue({
      deleteGoal: deleteGoalMock,
      isDeletingGoal: false,
      deleteGoalError: 'Falha ao remover o objetivo.',
      resetDeleteGoal: vi.fn(),
    })
    const { result } = renderHook(() => useGoalDetailPage({ goalId }), {
      wrapper: createWrapper(),
    })

    act(() => result.current.handleOpenConfirmDialog())
    expect(result.current.isConfirmDialogOpen).toBe(true)
    expect(result.current.deleteGoalError).toBe('Falha ao remover o objetivo.')
  })
})
