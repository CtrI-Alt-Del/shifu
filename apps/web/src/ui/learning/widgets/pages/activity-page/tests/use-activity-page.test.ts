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

  it('verifies an ordering and submits the same frozen sequence with its passage key', async () => {
    const orderingActivity: ChoiceActivityDetail = {
      ...activity,
      questions: [
        {
          key: 'order-1',
          kind: 'ordering',
          prompt: 'Organize as etapas.',
          steps: [
            { key: 'wash', text: 'Lavar' },
            { key: 'cut', text: 'Cortar' },
            { key: 'cook', text: 'Cozinhar' },
          ],
          initialOrderedStepKeys: ['wash', 'cut', 'cook'],
          verified: null,
        },
      ],
    }
    const uuidMock = vi
      .fn()
      .mockReturnValueOnce('passage-key')
      .mockReturnValueOnce('submission-key')
    vi.stubGlobal('crypto', { randomUUID: uuidMock })
    const onPreviewMock = vi.fn().mockResolvedValue({
      status: 'conclusive',
      score: 100,
      isCorrect: true,
      explanation: 'Correto.',
    })
    const onSubmitMock = vi.fn().mockResolvedValue(submitted)
    const { result } = renderHook(
      () =>
        useActivityPage({
          activity: orderingActivity,
          onPreview: onPreviewMock,
          onSubmit: onSubmitMock,
        }),
      { wrapper: wrapper() },
    )

    act(() => result.current.handleOrderingOrderChange(['cut', 'wash', 'cook']))
    await act(async () => result.current.handleContinue())

    expect(onPreviewMock).toHaveBeenCalledWith(
      'order-1',
      'revision-1',
      {
        kind: 'ordering',
        questionKey: 'order-1',
        orderedStepKeys: ['cut', 'wash', 'cook'],
      },
      'passage-key',
    )
    expect(result.current.feedback?.score).toBe(100)
    await act(async () => result.current.handleContinue())
    expect(onSubmitMock).toHaveBeenCalledWith({
      activityRevision: 'revision-1',
      answers: [
        {
          kind: 'ordering',
          questionKey: 'order-1',
          orderedStepKeys: ['cut', 'wash', 'cook'],
        },
      ],
      passageKey: 'passage-key',
      submissionKey: 'submission-key',
    })
  })

  it('submits ordering and translation together while preserving their distinct verification rules', async () => {
    const mixedActivity: ChoiceActivityDetail = {
      ...activity,
      questions: [
        {
          key: 'order-1',
          kind: 'ordering',
          prompt: 'Organize as etapas.',
          steps: [
            { key: 'wash', text: 'Lavar' },
            { key: 'cut', text: 'Cortar' },
            { key: 'cook', text: 'Cozinhar' },
          ],
          initialOrderedStepKeys: ['cut', 'wash', 'cook'],
          verified: null,
        },
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
        activity.questions[0],
      ],
    }
    vi.stubGlobal('crypto', {
      randomUUID: vi
        .fn()
        .mockReturnValueOnce('passage-key')
        .mockReturnValueOnce('submission-key'),
    })
    const onPreview = vi.fn().mockResolvedValue({ status: 'conclusive', score: 100 })
    const onSubmit = vi.fn().mockResolvedValue(submitted)
    const { result } = renderHook(
      () => useActivityPage({ activity: mixedActivity, onPreview, onSubmit }),
      { wrapper: wrapper() },
    )

    act(() => result.current.handleOrderingOrderChange(['wash', 'cut', 'cook']))
    await act(async () => result.current.handleContinue())
    act(() => result.current.handleOrderingOrderChange(['cook', 'cut', 'wash']))
    expect(result.current.currentOrderingOrder).toEqual(['wash', 'cut', 'cook'])
    await act(async () => result.current.handleContinue())
    expect(result.current.currentQuestion?.kind).toBe('translation')

    act(() => result.current.handleTranslationAnswerChange('Good moorning'))
    await act(async () => result.current.handleContinue())
    act(() => result.current.handleTranslationAnswerChange('Good morning'))
    expect(result.current.feedback).toBeNull()
    await act(async () => result.current.handleContinue())
    expect(onPreview).toHaveBeenLastCalledWith('translation-1', 'revision-1', {
      kind: 'translation',
      questionKey: 'translation-1',
      text: 'Good morning',
    })
    await act(async () => result.current.handleContinue())
    act(() => result.current.handleToggleOption('a'))
    await act(async () => result.current.handleContinue())
    await act(async () => result.current.handleContinue())

    expect(onSubmit).toHaveBeenCalledWith({
      activityRevision: 'revision-1',
      passageKey: 'passage-key',
      submissionKey: 'submission-key',
      answers: [
        {
          kind: 'ordering',
          questionKey: 'order-1',
          orderedStepKeys: ['wash', 'cut', 'cook'],
        },
        { kind: 'translation', questionKey: 'translation-1', text: 'Good morning' },
        { kind: 'single_choice', questionKey: 'single-1', selectedOptionKeys: ['a'] },
      ],
    })
  })

  describe('ordering recovery and immutable passage', () => {
    function makeActivity(
      overrides: Partial<ChoiceActivityDetail> = {},
    ): ChoiceActivityDetail {
      return {
        ...activity,
        questions: [
          {
            key: 'order-1',
            kind: 'ordering',
            prompt: 'Organize as etapas.',
            steps: [
              { key: 'wash', text: 'Lavar' },
              { key: 'cut', text: 'Cortar' },
              { key: 'cook', text: 'Cozinhar' },
            ],
            initialOrderedStepKeys: ['cut', 'wash', 'cook'],
            verified: null,
          },
        ],
        ...overrides,
      }
    }

    it('restores verified feedback after reload and submits the persisted passage without another preview', async () => {
      const base = makeActivity()
      const question = base.questions[0]
      if (question.kind !== 'ordering') throw new Error('Expected ordering fixture')
      const saved = {
        orderedStepKeys: ['wash', 'cut', 'cook'],
        score: 100,
        isCorrect: true,
        explanation: 'Sequência verificada.',
      }
      const restored = makeActivity({
        orderingPassageKey: 'persisted-passage',
        questions: [{ ...question, verified: saved }],
      })
      const onPreview = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(submitted)
      vi.stubGlobal('crypto', { randomUUID: vi.fn().mockReturnValue('new-submission') })
      const { result } = renderHook(
        () => useActivityPage({ activity: restored, onPreview, onSubmit }),
        { wrapper: wrapper() },
      )

      expect(result.current.currentOrderingOrder).toEqual(saved.orderedStepKeys)
      expect(result.current.feedback).toEqual({
        status: 'conclusive',
        ...saved,
        orderedStepKeys: undefined,
      })
      expect(result.current.isOrderingVerified).toBe(true)
      expect(result.current.hasUnsentAnswers).toBe(false)
      act(() => result.current.handleOrderingOrderChange(['cook', 'cut', 'wash']))
      expect(result.current.currentOrderingOrder).toEqual(saved.orderedStepKeys)
      await act(async () => result.current.handleContinue())
      expect(onPreview).not.toHaveBeenCalled()
      expect(onSubmit).toHaveBeenCalledWith({
        activityRevision: 'revision-1',
        answers: [
          {
            kind: 'ordering',
            questionKey: 'order-1',
            orderedStepKeys: saved.orderedStepKeys,
          },
        ],
        passageKey: 'persisted-passage',
        submissionKey: 'new-submission',
      })
    })

    it('retries a failed verification with its frozen order and original passage, then retries submission idempotently', async () => {
      const onPreview = vi
        .fn()
        .mockRejectedValueOnce(new Error('offline'))
        .mockResolvedValue({
          status: 'conclusive',
          score: 0,
          isCorrect: false,
          explanation: 'Revise a sequência.',
        })
      const onSubmit = vi
        .fn()
        .mockRejectedValueOnce(new Error('offline'))
        .mockResolvedValue(submitted)
      const randomUUID = vi
        .fn()
        .mockReturnValueOnce('same-passage')
        .mockReturnValueOnce('same-submission')
      vi.stubGlobal('crypto', { randomUUID })
      const { result } = renderHook(
        () => useActivityPage({ activity: makeActivity(), onPreview, onSubmit }),
        { wrapper: wrapper() },
      )
      act(() => result.current.handleOrderingOrderChange(['cook', 'cut', 'wash']))
      await act(async () => result.current.handleContinue())
      expect(result.current.hasFeedbackError).toBe(true)
      expect(result.current.hasUnsentAnswers).toBe(true)
      act(() => result.current.handleOrderingOrderChange(['wash', 'cut', 'cook']))
      expect(result.current.currentOrderingOrder).toEqual(['cook', 'cut', 'wash'])
      await act(async () => result.current.handleContinue())
      expect(onPreview.mock.calls[1]).toEqual(onPreview.mock.calls[0])
      expect(result.current.feedback?.isCorrect).toBe(false)
      expect(result.current.hasUnsentAnswers).toBe(false)
      await act(async () => result.current.handleContinue())
      expect(result.current.hasSubmissionError).toBe(true)
      await act(async () => result.current.handleContinue())
      expect(onSubmit.mock.calls[1]).toEqual(onSubmit.mock.calls[0])
      expect(randomUUID).toHaveBeenCalledTimes(2)
      expect(result.current.hasSubmissionError).toBe(false)
    })

    it.each([
      ['missing', ['wash', 'cut']],
      ['duplicate', ['wash', 'wash', 'cook']],
      ['unknown', ['wash', 'cut', 'unknown']],
    ])('does not preview an invalid %s permutation', async (_name, order) => {
      const onPreview = vi.fn()
      const { result } = renderHook(
        () => useActivityPage({ activity: makeActivity(), onPreview, onSubmit: vi.fn() }),
        { wrapper: wrapper() },
      )
      act(() => result.current.handleOrderingOrderChange(order))
      expect(result.current.canContinue).toBe(false)
      await act(async () => result.current.handleContinue())
      expect(onPreview).not.toHaveBeenCalled()
    })
  })

  describe('image choice question', () => {
    const imageActivity: ChoiceActivityDetail = {
      ...activity,
      questions: [
        activity.questions[0],
        {
          key: 'image-1',
          kind: 'image_choice',
          prompt: 'Qual destas cebolas está caramelizada?',
          options: [
            {
              key: 'opt-1',
              imagePath: '/curriculum/images/2d165276ed215938.webp',
              description: 'Crua.',
            },
            {
              key: 'opt-2',
              imagePath: '/curriculum/images/5c8a6a6b47848a6f.webp',
              description: 'Marrom.',
            },
            {
              key: 'opt-3',
              imagePath: '/curriculum/images/655fecc77404ac40.webp',
              description: 'Escura.',
            },
          ],
        },
      ],
    }

    function renderImageActivity() {
      const onPreviewMock = vi.fn().mockResolvedValue({
        status: 'conclusive',
        score: 0,
        isCorrect: false,
        optionFeedback: 'Essa cebola queimou.',
        explanation: 'Revise a cor.',
      })
      const onSubmitMock = vi.fn().mockResolvedValue(submitted)
      const rendered = renderHook(
        () =>
          useActivityPage({
            activity: imageActivity,
            onPreview: onPreviewMock,
            onSubmit: onSubmitMock,
          }),
        { wrapper: wrapper() },
      )
      return { ...rendered, onPreviewMock, onSubmitMock }
    }

    async function reachImageQuestion(
      result: ReturnType<typeof renderImageActivity>['result'],
    ) {
      act(() => result.current.handleToggleOption('a'))
      await act(async () => result.current.handleContinue())
      await act(async () => result.current.handleContinue())
      expect(result.current.currentQuestion?.kind).toBe('image_choice')
    }

    it('changes the chosen image freely before verifying and requires a selection to verify', async () => {
      const { result, onPreviewMock } = renderImageActivity()
      await reachImageQuestion(result)

      expect(result.current.selectedOptionKeys).toEqual([])
      await act(async () => result.current.handleContinue())
      expect(onPreviewMock).toHaveBeenCalledTimes(1)
      act(() => result.current.handleToggleOption('opt-1'))
      act(() => result.current.handleToggleOption('opt-3'))
      expect(result.current.selectedOptionKeys).toEqual(['opt-3'])
      act(() => result.current.handleToggleOption('unknown'))
      expect(result.current.selectedOptionKeys).toEqual(['opt-3'])
      expect(result.current.hasUnsentAnswers).toBe(true)
    })

    it('verifies exactly one key with the revision, then locks the choice', async () => {
      const { result, onPreviewMock } = renderImageActivity()
      await reachImageQuestion(result)

      act(() => result.current.handleToggleOption('opt-3'))
      await act(async () => result.current.handleContinue())

      expect(onPreviewMock).toHaveBeenLastCalledWith('image-1', 'revision-1', {
        kind: 'image_choice',
        questionKey: 'image-1',
        selectedOptionKeys: ['opt-3'],
      })
      expect(result.current.feedback).toMatchObject({
        isCorrect: false,
        optionFeedback: 'Essa cebola queimou.',
      })
      expect(result.current.isLastQuestion).toBe(true)
      act(() => result.current.handleToggleOption('opt-1'))
      expect(result.current.selectedOptionKeys).toEqual(['opt-3'])
    })

    it('keeps the frozen image after a transport failure and retries the same answer', async () => {
      const { result, onPreviewMock } = renderImageActivity()
      await reachImageQuestion(result)
      onPreviewMock.mockRejectedValueOnce(new Error('offline'))

      act(() => result.current.handleToggleOption('opt-2'))
      await act(async () => result.current.handleContinue())
      expect(result.current.hasFeedbackError).toBe(true)
      expect(result.current.feedback).toBeNull()
      act(() => result.current.handleToggleOption('opt-3'))
      expect(result.current.selectedOptionKeys).toEqual(['opt-2'])

      await act(async () => result.current.handleContinue())
      expect(onPreviewMock).toHaveBeenLastCalledWith('image-1', 'revision-1', {
        kind: 'image_choice',
        questionKey: 'image-1',
        selectedOptionKeys: ['opt-2'],
      })
      expect(result.current.feedback?.status).toBe('conclusive')
    })

    it('submits the single chosen image with the discriminator after the verification', async () => {
      const { result, onSubmitMock } = renderImageActivity()
      vi.stubGlobal('crypto', { randomUUID: vi.fn().mockReturnValue('submission-key') })
      await reachImageQuestion(result)

      act(() => result.current.handleToggleOption('opt-2'))
      await act(async () => result.current.handleContinue())
      await act(async () => result.current.handleContinue())

      expect(onSubmitMock).toHaveBeenCalledWith({
        activityRevision: 'revision-1',
        submissionKey: 'submission-key',
        answers: [
          { kind: 'single_choice', questionKey: 'single-1', selectedOptionKeys: ['a'] },
          { kind: 'image_choice', questionKey: 'image-1', selectedOptionKeys: ['opt-2'] },
        ],
      })
    })

    it('reverifies the same image and never submits while the verification is inconclusive', async () => {
      const { result, onPreviewMock, onSubmitMock } = renderImageActivity()
      await reachImageQuestion(result)
      onPreviewMock.mockResolvedValue({ status: 'inconclusive', score: null })

      act(() => result.current.handleToggleOption('opt-2'))
      await act(async () => result.current.handleContinue())
      await act(async () => result.current.handleContinue())

      expect(onPreviewMock).toHaveBeenCalledTimes(3)
      expect(result.current.feedback?.status).toBe('inconclusive')
      expect(onSubmitMock).not.toHaveBeenCalled()
    })
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
