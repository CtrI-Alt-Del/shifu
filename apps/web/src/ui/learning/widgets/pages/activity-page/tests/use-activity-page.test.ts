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

  describe('pair matching', () => {
    const pairActivity: ChoiceActivityDetail = {
      ...activity,
      questions: [
        {
          key: 'pairs-1',
          kind: 'pair_matching',
          prompt: 'Associe as palavras.',
          sourceLanguage: 'en',
          targetLanguage: 'pt-BR',
          words: [
            { key: 'word-0', text: 'dog' },
            { key: 'word-1', text: 'house' },
          ],
          translations: [
            { key: 'translation-1', text: 'casa' },
            { key: 'translation-0', text: 'cachorro' },
          ],
        },
      ],
    }
    const allPairs = [
      { wordKey: 'word-0', translationKey: 'translation-0' },
      { wordKey: 'word-1', translationKey: 'translation-1' },
    ]

    it('allows verifying only when every pair is formed, even if wrong', async () => {
      const onPreview = vi.fn().mockResolvedValue({ status: 'conclusive', score: 0 })
      const { result } = renderHook(
        () => useActivityPage({ activity: pairActivity, onPreview, onSubmit: vi.fn() }),
        { wrapper: wrapper() },
      )

      expect(result.current.canContinue).toBe(false)
      act(() =>
        result.current.handlePairMatchingAnswerChange([
          { wordKey: 'word-0', translationKey: 'translation-0' },
        ]),
      )
      expect(result.current.canContinue).toBe(false)
      await act(async () => result.current.handleContinue())
      expect(onPreview).not.toHaveBeenCalled()

      act(() =>
        result.current.handlePairMatchingAnswerChange([
          { wordKey: 'word-0', translationKey: 'translation-1' },
          { wordKey: 'word-1', translationKey: 'translation-0' },
        ]),
      )
      expect(result.current.canContinue).toBe(true)
      await act(async () => result.current.handleContinue())
      expect(onPreview).toHaveBeenCalledWith('pairs-1', 'revision-1', {
        kind: 'pair_matching',
        questionKey: 'pairs-1',
        pairs: [
          { wordKey: 'word-0', translationKey: 'translation-1' },
          { wordKey: 'word-1', translationKey: 'translation-0' },
        ],
      })
    })

    it('rejects pairs that repeat an item or use unknown keys', () => {
      const { result } = renderHook(
        () =>
          useActivityPage({
            activity: pairActivity,
            onPreview: vi.fn(),
            onSubmit: vi.fn(),
          }),
        { wrapper: wrapper() },
      )

      act(() =>
        result.current.handlePairMatchingAnswerChange([
          { wordKey: 'word-0', translationKey: 'translation-0' },
          { wordKey: 'word-1', translationKey: 'translation-0' },
        ]),
      )
      expect(result.current.canContinue).toBe(false)
      act(() =>
        result.current.handlePairMatchingAnswerChange([
          { wordKey: 'word-0', translationKey: 'translation-0' },
          { wordKey: 'word-9', translationKey: 'translation-1' },
        ]),
      )
      expect(result.current.canContinue).toBe(false)
    })

    it('keeps the verified answer read-only and submits exactly those pairs', async () => {
      const onPreview = vi.fn().mockResolvedValue({
        status: 'conclusive',
        score: 100,
        outcome: 'full',
        correctPairCount: 2,
        totalPairCount: 2,
      })
      const onSubmit = vi.fn().mockResolvedValue(submitted)
      vi.stubGlobal('crypto', { randomUUID: () => 'pairs-key' })
      const { result } = renderHook(
        () => useActivityPage({ activity: pairActivity, onPreview, onSubmit }),
        { wrapper: wrapper() },
      )

      act(() => result.current.handlePairMatchingAnswerChange(allPairs))
      await act(async () => result.current.handleContinue())
      expect(result.current.feedback?.outcome).toBe('full')

      act(() =>
        result.current.handlePairMatchingAnswerChange([
          { wordKey: 'word-0', translationKey: 'translation-1' },
          { wordKey: 'word-1', translationKey: 'translation-0' },
        ]),
      )
      expect(result.current.pairMatchingPairs).toEqual(allPairs)
      expect(result.current.feedback?.outcome).toBe('full')
      expect(onPreview).toHaveBeenCalledTimes(1)

      await act(async () => result.current.handleContinue())
      expect(onSubmit).toHaveBeenCalledWith({
        submissionKey: 'pairs-key',
        activityRevision: 'revision-1',
        answers: [{ kind: 'pair_matching', questionKey: 'pairs-1', pairs: allPairs }],
      })
    })

    it('keeps the formed pairs after a preliminary transport failure and retries them', async () => {
      const onPreview = vi
        .fn()
        .mockRejectedValueOnce(new Error('offline'))
        .mockResolvedValueOnce({ status: 'conclusive', score: 100, outcome: 'full' })
      const { result } = renderHook(
        () => useActivityPage({ activity: pairActivity, onPreview, onSubmit: vi.fn() }),
        { wrapper: wrapper() },
      )

      act(() => result.current.handlePairMatchingAnswerChange(allPairs))
      await act(async () => result.current.handleContinue())
      expect(result.current.hasFeedbackError).toBe(true)
      expect(result.current.feedback).toBeNull()
      expect(result.current.pairMatchingPairs).toEqual(allPairs)

      await act(async () => result.current.handleContinue())
      expect(onPreview).toHaveBeenCalledTimes(2)
      expect(onPreview.mock.calls[1]).toEqual(onPreview.mock.calls[0])
      expect(result.current.feedback?.outcome).toBe('full')
    })
  })
})
