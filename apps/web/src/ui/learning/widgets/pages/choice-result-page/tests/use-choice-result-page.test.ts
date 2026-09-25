import { act, cleanup, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ChoiceAttemptDetail } from '@/core/learning/choice-activity'

import {
  useChoiceResultPage,
  type ChoiceResultPageProps,
} from '../use-choice-result-page'

const ATTEMPT: ChoiceAttemptDetail = {
  attemptId: 'attempt-1',
  activityId: 'activity-1',
  status: 'failed',
  submittedAt: '2026-09-23T12:00:00Z',
  retryAllowed: true,
}

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useChoiceResultPage', () => {
  afterEach(cleanup)

  it('does not expose retry for pending or non-retryable failures', () => {
    const onRetryEvaluationMock = vi.fn()
    const pendingProps: ChoiceResultPageProps = {
      state: 'result',
      activity: {
        activityId: 'activity-1',
        title: 'Atividade',
        difficulty: 'easy',
        canSubmit: true,
        latestAttemptId: 'attempt-1',
        unresolvedAttemptId: 'attempt-1',
        questions: [],
      },
      attempt: { ...ATTEMPT, status: 'pending' },
      onRetryEvaluation: onRetryEvaluationMock,
    }
    const { result, rerender } = renderHook(
      ({ props }: { props: ChoiceResultPageProps }) => useChoiceResultPage(props),
      { initialProps: { props: pendingProps }, wrapper: createWrapper() },
    )

    expect(result.current.canRetry).toBe(false)
    rerender({
      props: {
        ...pendingProps,
        attempt: { ...ATTEMPT, retryAllowed: false },
      },
    })
    expect(result.current.canRetry).toBe(false)
    expect(result.current.pageState).toBe('result')
  })

  it('retries an allowed failure, reports a recoverable retry error and guards duplicate attempts', async () => {
    const onRetryEvaluationMock = vi.fn().mockRejectedValue(new Error('unavailable'))
    const props: ChoiceResultPageProps = {
      state: 'result',
      activity: {
        activityId: 'activity-1',
        title: 'Atividade',
        difficulty: 'easy',
        canSubmit: true,
        latestAttemptId: 'attempt-1',
        unresolvedAttemptId: 'attempt-1',
        questions: [],
      },
      attempt: ATTEMPT,
      onRetryEvaluation: onRetryEvaluationMock,
    }
    const { result } = renderHook(() => useChoiceResultPage(props), {
      wrapper: createWrapper(),
    })

    expect(result.current.canRetry).toBe(true)
    await act(async () => result.current.handleRetryEvaluation())
    expect(onRetryEvaluationMock).toHaveBeenCalledOnce()
    expect(result.current.hasRetryError).toBe(true)
    expect(result.current.isRetrying).toBe(false)

    await act(async () => result.current.handleRetryEvaluation())
    expect(onRetryEvaluationMock).toHaveBeenCalledTimes(2)
  })
})
