import { act, cleanup, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type {
  ChoiceActivityDetail,
  ChoiceSubmissionResult,
  PreliminaryQuestionResult,
} from '@/core/learning/choice-activity'
import type { CodePracticeRunner } from '@/core/learning/code-practice-runner'
import { FillBlanksQuestionFaker } from '@/core/learning/fakers'
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
const fillBlanksActivity: ChoiceActivityDetail = {
  ...activity,
  questions: [
    FillBlanksQuestionFaker.fake({
      segments: [
        { text: 'She ', blankKey: null },
        { text: null, blankKey: 'b1' },
        { text: ' to school and ', blankKey: null },
        { text: null, blankKey: 'b2' },
        { text: '.', blankKey: null },
      ],
      bank: [
        { key: 'w1', word: 'goes' },
        { key: 'w2', word: 'does' },
        { key: 'w3', word: 'go' },
      ],
    }),
    activity.questions[0],
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

  it('checks a complete fill, lets it be edited, re-checks it and submits the final placements', async () => {
    const onPreview = vi.fn().mockResolvedValue({
      status: 'conclusive',
      score: 50,
      correctBlankCount: 1,
      blankCount: 2,
    })
    const onSubmit = vi.fn().mockResolvedValue(submitted)
    vi.stubGlobal('crypto', { randomUUID: () => 'stable-key' })
    const { result } = renderHook(
      () => useActivityPage({ activity: fillBlanksActivity, onPreview, onSubmit }),
      { wrapper: wrapper() },
    )

    expect(result.current.canContinue).toBe(false)
    act(() => result.current.handleFillBlanksChange([{ blankKey: 'b1', wordKey: 'w1' }]))
    expect(result.current.fillBlanksPlacements).toEqual([
      { blankKey: 'b1', wordKey: 'w1' },
    ])
    expect(result.current.canContinue).toBe(false)
    expect(result.current.hasUnsentAnswers).toBe(true)

    act(() =>
      result.current.handleFillBlanksChange([
        { blankKey: 'b1', wordKey: 'w1' },
        { blankKey: 'b2', wordKey: 'w3' },
      ]),
    )
    expect(result.current.canContinue).toBe(true)
    await act(async () => result.current.handleContinue())

    expect(onPreview).toHaveBeenCalledWith('fill-1', 'revision-1', {
      kind: 'fill_blanks',
      questionKey: 'fill-1',
      placements: [
        { blankKey: 'b1', wordKey: 'w1' },
        { blankKey: 'b2', wordKey: 'w3' },
      ],
    })
    expect(result.current.feedback).toMatchObject({ score: 50, correctBlankCount: 1 })
    expect(result.current.frozenAnswer).toBeNull()
    expect(result.current.currentQuestionNumber).toBe(1)

    act(() =>
      result.current.handleFillBlanksChange([
        { blankKey: 'b1', wordKey: 'w1' },
        { blankKey: 'b2', wordKey: 'w2' },
      ]),
    )
    expect(result.current.feedback).toBeNull()
    expect(result.current.canContinue).toBe(true)
    await act(async () => result.current.handleContinue())
    expect(onPreview).toHaveBeenCalledTimes(2)
    expect(onPreview).toHaveBeenLastCalledWith('fill-1', 'revision-1', {
      kind: 'fill_blanks',
      questionKey: 'fill-1',
      placements: [
        { blankKey: 'b1', wordKey: 'w1' },
        { blankKey: 'b2', wordKey: 'w2' },
      ],
    })

    act(() => result.current.handleContinue())
    expect(result.current.currentQuestionNumber).toBe(2)
    expect(result.current.fillBlanksPlacements).toEqual([])
    act(() => result.current.handleToggleOption('a'))
    await act(async () => result.current.handleContinue())
    await act(async () => result.current.handleContinue())

    expect(onSubmit).toHaveBeenCalledWith({
      submissionKey: 'stable-key',
      activityRevision: 'revision-1',
      answers: [
        {
          kind: 'fill_blanks',
          questionKey: 'fill-1',
          placements: [
            { blankKey: 'b1', wordKey: 'w1' },
            { blankKey: 'b2', wordKey: 'w2' },
          ],
        },
        { kind: 'single_choice', questionKey: 'single-1', selectedOptionKeys: ['a'] },
      ],
    })
  })

  it('ignores fill-blanks edits while a check is in flight and after it settles accepts them', async () => {
    let finishCheck: (value: PreliminaryQuestionResult) => void = () => undefined
    const onPreview = vi.fn(
      () =>
        new Promise<PreliminaryQuestionResult>((resolve) => {
          finishCheck = resolve
        }),
    )
    const { result } = renderHook(
      () =>
        useActivityPage({ activity: fillBlanksActivity, onPreview, onSubmit: vi.fn() }),
      { wrapper: wrapper() },
    )
    const complete = [
      { blankKey: 'b1', wordKey: 'w1' },
      { blankKey: 'b2', wordKey: 'w2' },
    ]
    act(() => result.current.handleFillBlanksChange(complete))

    let checking: Promise<unknown> = Promise.resolve()
    act(() => {
      checking = Promise.resolve(result.current.handleContinue())
    })
    expect(result.current.isAssessing).toBe(true)
    expect(result.current.isFillBlanksLocked).toBe(true)
    act(() => result.current.handleFillBlanksChange([]))
    expect(result.current.fillBlanksPlacements).toEqual(complete)

    await act(async () => {
      finishCheck({
        status: 'conclusive',
        score: 100,
        correctBlankCount: 2,
        blankCount: 2,
      })
      await checking
    })
    expect(result.current.isFillBlanksLocked).toBe(false)
    act(() => result.current.handleFillBlanksChange([]))
    expect(result.current.fillBlanksPlacements).toEqual([])
    expect(result.current.feedback).toBeNull()
  })

  it('does not submit a fill-blanks last question that has no conclusive check', async () => {
    const lastFill: ChoiceActivityDetail = {
      ...fillBlanksActivity,
      questions: [...fillBlanksActivity.questions].reverse(),
    }
    const onPreview = vi.fn().mockResolvedValue({ status: 'conclusive', score: 100 })
    const onSubmit = vi.fn().mockResolvedValue(submitted)
    const { result } = renderHook(
      () => useActivityPage({ activity: lastFill, onPreview, onSubmit }),
      { wrapper: wrapper() },
    )
    act(() => result.current.handleToggleOption('a'))
    await act(async () => result.current.handleContinue())
    act(() => result.current.handleContinue())
    act(() =>
      result.current.handleFillBlanksChange([
        { blankKey: 'b1', wordKey: 'w1' },
        { blankKey: 'b2', wordKey: 'w2' },
      ]),
    )
    expect(result.current.isLastQuestion).toBe(true)

    await act(async () => result.current.handleContinue())
    expect(onPreview).toHaveBeenCalledTimes(2)
    expect(onSubmit).not.toHaveBeenCalled()
    expect(result.current.feedback?.status).toBe('conclusive')

    await act(async () => result.current.handleContinue())
    expect(onSubmit).toHaveBeenCalledTimes(1)
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

  it('lets code change after feedback and assesses the updated answer', async () => {
    const onPreview = vi
      .fn()
      .mockResolvedValueOnce({ status: 'conclusive', score: 25 })
      .mockResolvedValueOnce({ status: 'conclusive', score: 100 })
    const codeActivity = { ...activity, questions: [activity.questions[1]] }
    const { result } = renderHook(
      () => useActivityPage({ activity: codeActivity, onPreview, onSubmit: vi.fn() }),
      { wrapper: wrapper() },
    )

    await act(async () =>
      result.current.handleAssessCode([{ path: 'index.js', content: 'return ""' }]),
    )
    expect(result.current.feedback?.score).toBe(25)
    act(() =>
      result.current.handleCodeFilesChange([
        { path: 'index.js', content: 'return "positivo"' },
      ]),
    )
    expect(result.current.feedback).toBeNull()
    expect(result.current.frozenAnswer).toBeNull()

    await act(async () =>
      result.current.handleAssessCode([
        { path: 'index.js', content: 'return "positivo"' },
      ]),
    )
    expect(onPreview).toHaveBeenCalledTimes(2)
    expect(onPreview).toHaveBeenLastCalledWith('code-1', 'revision-1', {
      kind: 'javascript_stdin',
      questionKey: 'code-1',
      files: [{ path: 'index.js', content: 'return "positivo"' }],
    })
    expect(result.current.feedback?.score).toBe(100)
  })

  it('previews, freezes, and submits a typed translation answer', async () => {
    const translationActivity: ChoiceActivityDetail = {
      ...activity,
      questions: [
        {
          key: 'translation-1',
          kind: 'translation',
          prompt: 'Traduza o texto.',
          sourceLanguage: 'pt-BR',
          targetLanguage: 'en-US',
          sourceText: 'Bom dia',
          criteria: [
            { key: 'semantic_preservation', name: 'Sentido', weightPercentage: 70 },
            { key: 'grammatical_adequacy', name: 'Gramática', weightPercentage: 30 },
          ],
        },
      ],
    }
    const onPreview = vi.fn().mockResolvedValue({ status: 'conclusive', score: 100 })
    const onSubmit = vi.fn().mockResolvedValue(submitted)
    vi.stubGlobal('crypto', { randomUUID: () => 'stable-key' })
    const { result } = renderHook(
      () => useActivityPage({ activity: translationActivity, onPreview, onSubmit }),
      { wrapper: wrapper() },
    )

    expect(result.current.canContinue).toBe(false)
    act(() => result.current.handleTranslationAnswerChange('Good morning'))
    expect(result.current.translationAnswerText).toBe('Good morning')
    expect(result.current.canContinue).toBe(true)

    await act(async () => result.current.handleContinue())
    expect(onPreview).toHaveBeenCalledWith('translation-1', 'revision-1', {
      kind: 'translation',
      questionKey: 'translation-1',
      text: 'Good morning',
    })
    expect(result.current.feedback?.score).toBe(100)

    await act(async () => result.current.handleContinue())
    expect(onSubmit).toHaveBeenCalledWith({
      submissionKey: 'stable-key',
      activityRevision: 'revision-1',
      answers: [
        { kind: 'translation', questionKey: 'translation-1', text: 'Good morning' },
      ],
    })
    expect(result.current.hasUnsentAnswers).toBe(false)
  })

  it('lets translation text change after feedback and reassesses the updated answer', async () => {
    const translationActivity: ChoiceActivityDetail = {
      ...activity,
      questions: [
        {
          key: 'translation-1',
          kind: 'translation',
          prompt: 'Traduza o texto.',
          sourceLanguage: 'pt-BR',
          targetLanguage: 'en-US',
          sourceText: 'Bom dia',
          criteria: [
            { key: 'semantic_preservation', name: 'Sentido', weightPercentage: 70 },
            { key: 'grammatical_adequacy', name: 'Gramática', weightPercentage: 30 },
          ],
        },
      ],
    }
    const onPreview = vi
      .fn()
      .mockResolvedValueOnce({ status: 'conclusive', score: 50 })
      .mockResolvedValueOnce({ status: 'conclusive', score: 100 })
    const { result } = renderHook(
      () =>
        useActivityPage({ activity: translationActivity, onPreview, onSubmit: vi.fn() }),
      { wrapper: wrapper() },
    )

    act(() => result.current.handleTranslationAnswerChange('Good moorning'))
    await act(async () => result.current.handleContinue())
    expect(result.current.feedback?.score).toBe(50)

    act(() => result.current.handleTranslationAnswerChange('Good morning'))
    expect(result.current.feedback).toBeNull()
    expect(result.current.frozenAnswer).toBeNull()

    await act(async () => result.current.handleContinue())
    expect(onPreview).toHaveBeenCalledTimes(2)
    expect(onPreview).toHaveBeenLastCalledWith('translation-1', 'revision-1', {
      kind: 'translation',
      questionKey: 'translation-1',
      text: 'Good morning',
    })
    expect(result.current.feedback?.score).toBe(100)
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
  it('submits the exact conclusive React answer with its discriminator and revision', async () => {
    const codeQuestion = activity.questions[1]
    if (codeQuestion.kind !== 'javascript_stdin') throw new Error('Invalid fixture')
    const question = {
      ...codeQuestion,
      kind: 'react' as const,
      additionalFilePolicy: null,
    }
    const reactActivity = { ...activity, questions: [question] }
    const onPreview = vi.fn().mockResolvedValue({ status: 'conclusive', score: 100 })
    const onSubmit = vi.fn().mockResolvedValue(submitted)
    vi.stubGlobal('crypto', { randomUUID: () => 'react-key' })
    const { result } = renderHook(
      () => useActivityPage({ activity: reactActivity, onPreview, onSubmit }),
      { wrapper: wrapper() },
    )
    const files = [{ path: 'index.js', content: 'exact React source' }]
    act(() => result.current.handleCodeFilesChange(files))
    await act(async () => result.current.handleAssessCode(files))
    act(() =>
      result.current.handleCodeFilesChange([
        { path: 'index.js', content: 'remote edit' },
      ]),
    )
    expect(result.current.feedback?.score).toBe(100)
    expect(result.current.frozenAnswer).toEqual({
      kind: 'react',
      questionKey: 'code-1',
      files,
    })
    await act(async () => result.current.handleContinue())
    expect(onSubmit).toHaveBeenCalledWith({
      activityRevision: 'revision-1',
      submissionKey: 'react-key',
      answers: [{ kind: 'react', questionKey: 'code-1', files }],
    })
  })
})
