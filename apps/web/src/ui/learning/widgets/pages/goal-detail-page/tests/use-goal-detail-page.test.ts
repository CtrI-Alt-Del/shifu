import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { GoalDetail } from '@/core/learning/goal-detail'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useGoalDetailPage } from '../use-goal-detail-page'
import { useGoalDetailQuery } from '../use-goal-detail-query'

vi.mock('../use-goal-detail-query', () => ({ useGoalDetailQuery: vi.fn() }))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({ useNavigation: vi.fn() }))

const useGoalDetailQueryMock = vi.mocked(useGoalDetailQuery)
const useNavigationMock = vi.mocked(useNavigation)
const navigateToMock = vi.fn()
const refetchGoalDetailMock = vi.fn()
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

describe('useGoalDetailPage', () => {
  beforeEach(() => {
    navigateToMock.mockReset()
    refetchGoalDetailMock.mockReset()
    useGoalDetailQueryMock.mockReset()
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock,
      navigateToGoalDetail: vi.fn(),
      navigateToPlanner: vi.fn(),
    })
    mockQuery()
  })

  it('starts in graph and classifies loading, empty, absence and recoverable states', () => {
    mockQuery({ isLoadingGoalDetail: true })
    const { result, rerender } = renderHook(
      ({ id }) => useGoalDetailPage({ goalId: id }),
      { initialProps: { id: goalId } },
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
    const { result } = renderHook(() => useGoalDetailPage({ goalId }))
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
    const { result } = renderHook(() => useGoalDetailPage({ goalId }))
    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('login'))
    expect(result.current.state).toBe('error')
  })
})
