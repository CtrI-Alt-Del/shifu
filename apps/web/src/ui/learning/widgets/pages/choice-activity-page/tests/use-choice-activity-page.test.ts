import { act, cleanup, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type {
  ChoiceActivityDetail,
  ChoiceSubmissionResult,
} from '@/core/learning/choice-activity'

import { useChoiceActivityPage } from '../use-choice-activity-page'

const ACTIVITY: ChoiceActivityDetail = {
  activityId: 'activity-1',
  title: 'Estruturas de repetição',
  difficulty: 'medium',
  canSubmit: true,
  latestAttemptId: null,
  unresolvedAttemptId: null,
  questions: [
    {
      key: 'single-1',
      kind: 'single_choice',
      prompt: 'Qual valor?',
      options: [
        { key: 'a', text: '1' },
        { key: 'b', text: '2' },
      ],
    },
    {
      key: 'multiple-1',
      kind: 'multiple_selection',
      prompt: 'Quais alternativas?',
      options: [
        { key: 'c', text: 'A' },
        { key: 'd', text: 'B' },
      ],
    },
  ],
}

const SUBMISSION_RESULT: ChoiceSubmissionResult = {
  attemptId: 'attempt-1',
  status: 'pending',
  resultUrl: '/learning/attempts/attempt-1',
}

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useChoiceActivityPage', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('validates single choice, advances only forward and submits the complete ordered answers', async () => {
    const onSubmitMock = vi.fn().mockResolvedValue(SUBMISSION_RESULT)
    vi.stubGlobal('crypto', { randomUUID: vi.fn().mockReturnValue('submission-key-1') })
    const { result } = renderHook(
      () => useChoiceActivityPage({ activity: ACTIVITY, onSubmit: onSubmitMock }),
      { wrapper: createWrapper() },
    )

    expect(result.current.canContinue).toBe(false)
    act(() => result.current.handleContinue())
    expect(result.current.currentQuestionNumber).toBe(1)

    act(() => result.current.handleToggleOption('a'))
    expect(result.current.canContinue).toBe(true)
    act(() => result.current.handleContinue())
    expect(result.current.currentQuestionNumber).toBe(2)
    expect(result.current.currentQuestion?.key).toBe('multiple-1')

    act(() => result.current.handleToggleOption('c'))
    act(() => result.current.handleToggleOption('d'))
    expect(result.current.selectedOptionKeys).toEqual(['c', 'd'])
    await act(async () => result.current.handleContinue())

    expect(onSubmitMock).toHaveBeenCalledWith({
      submissionKey: 'submission-key-1',
      answers: [
        { questionKey: 'single-1', selectedOptionKeys: ['a'] },
        { questionKey: 'multiple-1', selectedOptionKeys: ['c', 'd'] },
      ],
    })
    expect(result.current.currentQuestionNumber).toBe(2)
  })

  it('adds and removes multiple selections and preserves the submission key on transport retry', async () => {
    const onSubmitMock = vi
      .fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce(SUBMISSION_RESULT)
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn().mockReturnValue('stable-submission-key'),
    })
    const { result } = renderHook(
      () =>
        useChoiceActivityPage({
          activity: { ...ACTIVITY, questions: ACTIVITY.questions.slice(1) },
          onSubmit: onSubmitMock,
        }),
      { wrapper: createWrapper() },
    )

    act(() => result.current.handleToggleOption('c'))
    act(() => result.current.handleToggleOption('d'))
    act(() => result.current.handleToggleOption('c'))
    expect(result.current.selectedOptionKeys).toEqual(['d'])

    await act(async () => result.current.handleContinue())
    expect(result.current.hasSubmissionError).toBe(true)
    expect(result.current.isSubmissionLocked).toBe(true)
    expect(result.current.hasUnsentAnswers).toBe(true)
    act(() => result.current.handleToggleOption('c'))
    expect(result.current.selectedOptionKeys).toEqual(['d'])
    await act(async () => result.current.handleContinue())

    expect(onSubmitMock).toHaveBeenCalledTimes(2)
    expect(onSubmitMock.mock.calls[0][0].submissionKey).toBe('stable-submission-key')
    expect(onSubmitMock.mock.calls[1][0].submissionKey).toBe('stable-submission-key')
    expect(onSubmitMock.mock.calls[1][0].answers).toEqual(
      onSubmitMock.mock.calls[0][0].answers,
    )
  })

  it('warns before leaving while unsent answers remain in memory', () => {
    const onUnsentAnswersChangeMock = vi.fn()
    const { result } = renderHook(
      () =>
        useChoiceActivityPage({
          activity: ACTIVITY,
          onSubmit: vi.fn(),
          onUnsentAnswersChange: onUnsentAnswersChangeMock,
        }),
      { wrapper: createWrapper() },
    )
    act(() => result.current.handleToggleOption('a'))
    const event = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent
    window.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(result.current.hasUnsentAnswers).toBe(true)
    expect(onUnsentAnswersChangeMock).toHaveBeenLastCalledWith(true)
  })
})
