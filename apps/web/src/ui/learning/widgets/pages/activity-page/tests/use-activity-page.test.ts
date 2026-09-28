import { act, cleanup, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type {
  ChoiceActivityDetail,
  ChoiceSubmissionResult,
} from '@/core/learning/choice-activity'
import type { CodePracticeRunner } from '@/core/learning/code-practice-runner'
import { useActivityPage } from '../use-activity-page'

const activity: ChoiceActivityDetail = {
  activityId: 'activity-1',
  activityRevision: 'revision-1',
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
      key: 'code-1',
      kind: 'javascript_stdin',
      prompt: 'Resolva',
      initialFiles: [{ path: 'index.js', content: 'console.log(1)', editable: true }],
      entrypoint: 'index.js',
      editablePaths: ['index.js'],
      fixedDependencies: [],
      permittedCommands: [],
      criteria: [{ key: 'correct', name: 'Correção', weightPercentage: 100 }],
    },
  ],
}
const submitted: ChoiceSubmissionResult = {
  attemptId: 'attempt-1',
  status: 'pending',
  resultUrl: '/attempt-1',
}
function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client }, children)
}

describe('useActivityPage', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('preserves the injected code-practice runner factory', () => {
    const runnerFactory = vi.fn(() => ({}) as CodePracticeRunner)
    const { result } = renderHook(
      () => useActivityPage({ activity, onSubmit: vi.fn(), runnerFactory }),
      { wrapper: wrapper() },
    )

    expect(result.current.runnerFactory).toBe(runnerFactory)
  })

  it('preserves direct choice-only advance and submission without preliminary or revision', async () => {
    const legacyActivity = {
      ...activity,
      activityRevision: null,
      questions: [
        activity.questions[0],
        {
          key: 'multiple-1',
          kind: 'multiple_selection' as const,
          prompt: 'Selecione',
          options: [
            { key: 'c', text: 'C' },
            { key: 'd', text: 'D' },
          ],
        },
      ],
    }
    const onPreview = vi.fn()
    const onSubmit = vi.fn().mockResolvedValue(submitted)
    vi.stubGlobal('crypto', { randomUUID: () => 'legacy-key' })
    const { result } = renderHook(
      () => useActivityPage({ activity: legacyActivity, onPreview, onSubmit }),
      { wrapper: wrapper() },
    )
    act(() => result.current.handleToggleOption('a'))
    act(() => result.current.handleContinue())
    expect(result.current.currentQuestionNumber).toBe(2)
    act(() => result.current.handleToggleOption('c'))
    await act(async () => result.current.handleContinue())
    expect(onPreview).not.toHaveBeenCalled()
    expect(onSubmit).toHaveBeenCalledWith({
      submissionKey: 'legacy-key',
      answers: [
        { questionKey: 'single-1', selectedOptionKeys: ['a'] },
        { questionKey: 'multiple-1', selectedOptionKeys: ['c'] },
      ],
    })
  })

  it('submits diagnostic choices without preliminary feedback', async () => {
    const diagnosticActivity = {
      ...activity,
      isDiagnostic: true,
      questions: [activity.questions[0]],
    }
    const onPreview = vi.fn()
    const onSubmit = vi.fn().mockResolvedValue({ ...submitted, isDiagnostic: true })
    vi.stubGlobal('crypto', { randomUUID: () => 'diagnostic-key' })
    const { result } = renderHook(
      () => useActivityPage({ activity: diagnosticActivity, onPreview, onSubmit }),
      { wrapper: wrapper() },
    )

    act(() => result.current.handleToggleOption('a'))
    await act(async () => result.current.handleContinue())

    expect(onPreview).not.toHaveBeenCalled()
    expect(onSubmit).toHaveBeenCalledWith({
      submissionKey: 'diagnostic-key',
      activityRevision: 'revision-1',
      answers: [
        { kind: 'single_choice', questionKey: 'single-1', selectedOptionKeys: ['a'] },
      ],
    })
    expect(result.current.feedback).toBeNull()
  })

  it('submits the edited diagnostic code without an official preview', async () => {
    const diagnosticActivity = {
      ...activity,
      isDiagnostic: true,
      questions: [activity.questions[1]],
    }
    const onPreview = vi.fn()
    const onSubmit = vi.fn().mockResolvedValue({ ...submitted, isDiagnostic: true })
    vi.stubGlobal('crypto', { randomUUID: () => 'diagnostic-code-key' })
    const { result } = renderHook(
      () => useActivityPage({ activity: diagnosticActivity, onPreview, onSubmit }),
      { wrapper: wrapper() },
    )

    act(() =>
      result.current.handleCodeFilesChange([
        { path: 'index.js', content: 'console.log(2)' },
      ]),
    )
    await act(async () => result.current.handleContinue())

    expect(onPreview).not.toHaveBeenCalled()
    expect(onSubmit).toHaveBeenCalledWith({
      submissionKey: 'diagnostic-code-key',
      activityRevision: 'revision-1',
      answers: [
        {
          kind: 'javascript_stdin',
          questionKey: 'code-1',
          files: [{ path: 'index.js', content: 'console.log(2)' }],
        },
      ],
    })
  })
  it('previews in order, freezes editable source, and submits the complete revisioned answer set', async () => {
    const onPreview = vi.fn().mockResolvedValue({ status: 'conclusive', score: 75 })
    const onSubmit = vi.fn().mockResolvedValue(submitted)
    vi.stubGlobal('crypto', { randomUUID: () => 'stable-key' })
    const { result } = renderHook(
      () => useActivityPage({ activity, onPreview, onSubmit }),
      { wrapper: wrapper() },
    )
    expect(result.current.canContinue).toBe(false)
    act(() => result.current.handleToggleOption('a'))
    await act(async () => result.current.handleContinue())
    expect(onPreview).toHaveBeenCalledWith('single-1', 'revision-1', {
      kind: 'single_choice',
      questionKey: 'single-1',
      selectedOptionKeys: ['a'],
    })
    expect(result.current.currentQuestionNumber).toBe(1)
    act(() => result.current.handleContinue())
    expect(result.current.currentQuestionNumber).toBe(2)
    await act(async () =>
      result.current.handleAssessCode([{ path: 'index.js', content: 'console.log(2)' }]),
    )
    expect(onPreview).toHaveBeenLastCalledWith('code-1', 'revision-1', {
      kind: 'javascript_stdin',
      questionKey: 'code-1',
      files: [{ path: 'index.js', content: 'console.log(2)' }],
    })
    await act(async () => result.current.handleContinue())
    expect(onSubmit).toHaveBeenCalledWith({
      submissionKey: 'stable-key',
      activityRevision: 'revision-1',
      answers: [
        { kind: 'single_choice', questionKey: 'single-1', selectedOptionKeys: ['a'] },
        {
          kind: 'javascript_stdin',
          questionKey: 'code-1',
          files: [{ path: 'index.js', content: 'console.log(2)' }],
        },
      ],
    })
    expect(result.current.hasUnsentAnswers).toBe(false)
  })

  it('reassesses the same frozen answer after inconclusive feedback', async () => {
    const onPreview = vi
      .fn()
      .mockResolvedValueOnce({ status: 'inconclusive', score: null })
      .mockResolvedValueOnce({ status: 'conclusive', score: 100 })
    const { result } = renderHook(
      () => useActivityPage({ activity, onPreview, onSubmit: vi.fn() }),
      { wrapper: wrapper() },
    )
    act(() => result.current.handleToggleOption('b'))
    await act(async () => result.current.handleContinue())
    expect(result.current.feedback?.status).toBe('inconclusive')
    expect(result.current.currentQuestionNumber).toBe(1)
    await act(async () => result.current.handleContinue())
    expect(onPreview.mock.calls[1]).toEqual(onPreview.mock.calls[0])
    expect(result.current.feedback?.status).toBe('conclusive')
  })

  it('keeps the frozen source after a preliminary transport failure and retries it', async () => {
    const onPreview = vi
      .fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ status: 'conclusive', score: 75 })
    const { result } = renderHook(
      () => useActivityPage({ activity, onPreview, onSubmit: vi.fn() }),
      { wrapper: wrapper() },
    )
    act(() => result.current.handleToggleOption('a'))
    await act(async () => result.current.handleContinue())
    expect(result.current.hasFeedbackError).toBe(true)
    expect(result.current.frozenAnswer).toEqual({
      kind: 'single_choice',
      questionKey: 'single-1',
      selectedOptionKeys: ['a'],
    })
    act(() => result.current.handleToggleOption('b'))
    expect(result.current.selectedOptionKeys).toEqual(['a'])
    await act(async () => result.current.handleContinue())
    expect(onPreview.mock.calls[1]).toEqual(onPreview.mock.calls[0])
    expect(result.current.feedback?.status).toBe('conclusive')
  })

  it('keeps the submission key and unsent leave warning on transport failure', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce(submitted)
    const onUnsentAnswersChange = vi.fn()
    vi.stubGlobal('crypto', { randomUUID: () => 'stable-key' })
    const oneQuestion = { ...activity, questions: activity.questions.slice(0, 1) }
    const { result } = renderHook(
      () =>
        useActivityPage({
          activity: oneQuestion,
          onPreview: vi.fn().mockResolvedValue({ status: 'conclusive', score: 100 }),
          onSubmit,
          onUnsentAnswersChange,
        }),
      { wrapper: wrapper() },
    )
    act(() => result.current.handleToggleOption('a'))
    const event = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    expect(onUnsentAnswersChange).toHaveBeenLastCalledWith(true)
    await act(async () => result.current.handleContinue())
    await act(async () => result.current.handleContinue())
    expect(result.current.hasSubmissionError).toBe(true)
    expect(result.current.isSubmissionLocked).toBe(true)
    await act(async () => result.current.handleContinue())
    expect(onSubmit).toHaveBeenCalledTimes(2)
    expect(onSubmit.mock.calls[0][0]).toEqual(onSubmit.mock.calls[1][0])
  })
})
