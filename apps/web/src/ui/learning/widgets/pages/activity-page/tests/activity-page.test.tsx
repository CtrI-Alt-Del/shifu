import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  ChoiceActivityDetail,
  ImageChoiceQuestion as ImageQuestion,
} from '@/core/learning/choice-activity'
import { FillBlanksQuestionFaker } from '@/core/learning/fakers'
import type { HtmlCssJsQuestion as HtmlQuestion } from '@/core/learning/choice-activity'
import type { CodePracticeRunner } from '@/core/learning/code-practice-runner'
import {
  clearDiagnosticRun,
  setDiagnosticRun,
  setDiagnosticSequence,
} from '@/ui/learning/diagnostic-run-session'

import { ActivityPage } from '..'
import { CodeQuestion } from '../code-question'
import { HtmlCssJsQuestion } from '../html-css-js-question'
import type { ActivityPageController } from '../use-activity-page'
import { useActivityPage } from '../use-activity-page'
import { PairMatchingQuestion } from '../pair-matching-question'
import { createReactDraftStoreMock } from './react-draft-store-mock'
import type { CodeEditorProps } from '@/ui/learning/widgets/components/code-editor'

vi.mock('../use-activity-page', () => ({
  useActivityPage: vi.fn(),
}))
vi.mock('../code-question', () => ({ CodeQuestion: vi.fn(() => null) }))
vi.mock('../pair-matching-question', () => ({
  PairMatchingQuestion: vi.fn(() => <div data-testid='pair-matching-question' />),
}))
vi.mock('../html-css-js-question', () => ({
  HtmlCssJsQuestion: vi.fn(() => <div data-testid='html-css-js-question' />),
}))
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('@/ui/learning/widgets/components/code-editor', () => ({
  CodeEditor: ({ files, readOnly }: CodeEditorProps) => (
    <textarea
      aria-label='Editor React'
      value={files[0]?.content ?? ''}
      readOnly={readOnly}
    />
  ),
}))

const useActivityPageMock = vi.mocked(useActivityPage)

const ACTIVITY: ChoiceActivityDetail = {
  activityId: 'activity-1',
  title: 'Estruturas de repetição',
  difficulty: 'medium',
  canSubmit: true,
  latestAttemptId: null,
  unresolvedAttemptId: null,
  questions: [
    {
      key: 'question-1',
      kind: 'multiple_selection',
      prompt: 'Quais afirmações são verdadeiras?',
      options: [
        { key: 'a', text: 'O laço executa três vezes.' },
        { key: 'b', text: 'A condição é reavaliada.' },
      ],
    },
  ],
}

const CODE_QUESTION = {
  key: 'code-question-1',
  kind: 'javascript_stdin',
  prompt: 'Leia e imprima um número.',
  initialFiles: [{ path: 'index.js', content: 'console.log(1)', editable: true }],
  entrypoint: 'index.js',
  editablePaths: ['index.js'],
  fixedDependencies: [],
  permittedCommands: [],
  criteria: [{ key: 'correct', name: 'Correção', weightPercentage: 100 }],
} satisfies NonNullable<ActivityPageController['currentQuestion']>

const HTML_CSS_JS_QUESTION: HtmlQuestion = {
  key: 'web-question-1',
  kind: 'html_css_js',
  prompt: 'Crie uma página responsiva.',
  initialFiles: [{ path: 'index.html', content: '<main></main>', editable: true }],
  entrypoint: 'index.html',
  editablePaths: ['index.html'],
  fixedDependencies: [{ name: 'vite', version: '7.0.0' }],
  permittedCommands: [{ id: 'dev', executable: 'npm', arguments: ['run', 'dev'] }],
  criteria: [{ key: 'semantic', name: 'HTML semântico', weightPercentage: 100 }],
}

const ORDERING_QUESTION = {
  key: 'ordering-question-1',
  kind: 'ordering',
  prompt: 'Organize as etapas.',
  steps: [
    { key: 'wash', text: 'Lavar' },
    { key: 'cut', text: 'Cortar' },
    { key: 'cook', text: 'Cozinhar' },
  ],
  initialOrderedStepKeys: ['wash', 'cut', 'cook'],
  verified: null,
} as const

const IMAGE_QUESTION: ImageQuestion = {
  key: 'image-question-1',
  kind: 'image_choice',
  prompt: 'Qual destas cebolas está caramelizada?',
  options: [
    {
      key: 'opt-1',
      imagePath: '/curriculum/images/2d165276ed215938.webp',
      description: 'Fatias brancas e firmes.',
    },
    {
      key: 'opt-2',
      imagePath: '/curriculum/images/5c8a6a6b47848a6f.webp',
      description: 'Tiras marrons e macias.',
    },
    {
      key: 'opt-3',
      imagePath: '/curriculum/images/655fecc77404ac40.webp',
      description: 'Fatias escuras com bordas pretas.',
    },
  ],
}

function createControllerMock(
  overrides: Partial<ActivityPageController> = {},
): ActivityPageController {
  return {
    activity: ACTIVITY,
    runnerFactory: undefined,
    reactRunnerFactory: undefined,
    htmlCssJsRunnerFactory: undefined,
    reactFastifyRunnerFactory: undefined,
    reactDraftStore: createReactDraftStoreMock(),
    accountId: null,
    isOnlineAuthority: false,
    handleReactAnswerValidityChange: vi.fn(),
    isMixedActivity: false,
    canContinue: true,
    feedback: { status: 'conclusive', score: 100 },
    frozenAnswer: null,
    isAssessing: false,
    hasFeedbackError: false,
    handleAssessCode: vi.fn(),
    handleCodeFilesChange: vi.fn(),
    handleFillBlanksChange: vi.fn(),
    fillBlanksPlacements: [],
    isFillBlanksLocked: false,
    handleTranslationAnswerChange: vi.fn(),
    handlePairMatchingAnswerChange: vi.fn(),
    pairMatchingPairs: [],
    translationAnswerText: '',
    currentQuestion: ACTIVITY.questions[0],
    currentQuestionIndex: 0,
    currentQuestionNumber: 1,
    handleContinue: vi.fn(),
    handleRetryLoad: vi.fn(),
    handleReturnToSkill: vi.fn(),
    handleToggleOption: vi.fn(),
    currentOrderingOrder: [],
    handleOrderingOrderChange: vi.fn(),
    isOrderingVerified: false,
    hasSubmissionError: false,
    hasUnsentAnswers: true,
    isSubmissionLocked: false,
    isDiagnosticProcessing: false,
    diagnosticStatus: null,
    hasDiagnosticStatusError: false,
    diagnosticRetryError: false,
    diagnosticCompletionError: false,
    isRetryingDiagnostic: false,
    isCompletingDiagnostic: false,
    handleRetryDiagnostic: vi.fn(),
    handleRetryDiagnosticStatus: vi.fn(),
    handleRetryDiagnosticCompletion: vi.fn(),
    isLastQuestion: true,
    isLoading: false,
    isPrivateAbsence: false,
    isInvalidated: false,
    isDiagnosticEntryRequired: false,
    isRecoverableError: false,
    isSubmitting: false,
    selectedOptionKeys: ['a'],
    totalQuestions: 1,
    ...overrides,
  }
}

describe('ActivityPage', () => {
  beforeEach(() => {
    vi.mocked(CodeQuestion).mockClear()
    useActivityPageMock.mockReturnValue(createControllerMock())
    vi.stubGlobal('matchMedia', () => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    clearDiagnosticRun('goal-test', 'skill-test')
  })

  it('renders the ordering controls and the verify action', () => {
    const handleOrderingOrderChangeMock = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: {
          ...ACTIVITY,
          activityRevision: 'revision-1',
          questions: [ORDERING_QUESTION],
        },
        currentQuestion: ORDERING_QUESTION,
        currentOrderingOrder: ['wash', 'cut', 'cook'],
        handleOrderingOrderChange: handleOrderingOrderChangeMock,
        feedback: null,
        frozenAnswer: null,
        isOrderingVerified: false,
      }),
    )

    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: 'Mover para baixo: Lavar' }))
    expect(handleOrderingOrderChangeMock).toHaveBeenCalledWith(['cut', 'wash', 'cook'])
    expect(screen.getByRole('button', { name: 'Verificar' })).toBeEnabled()
  })

  it.each([
    {
      isCorrect: true,
      score: 100,
      label: 'Ordem correta',
      isLastQuestion: true,
      action: 'Enviar atividade',
    },
    {
      isCorrect: false,
      score: 0,
      label: 'Ordem incorreta',
      isLastQuestion: false,
      action: 'Próxima questão',
    },
  ])(
    'shows the provisional ordering outcome and delegates $action without reopening the sequence',
    ({ isCorrect, score, label, isLastQuestion, action }) => {
      const handleContinue = vi.fn()
      useActivityPageMock.mockReturnValue(
        createControllerMock({
          activity: { ...ACTIVITY, questions: [ORDERING_QUESTION] },
          isMixedActivity: true,
          currentQuestion: ORDERING_QUESTION,
          currentOrderingOrder: ['wash', 'cut', 'cook'],
          isOrderingVerified: true,
          feedback: {
            status: 'conclusive',
            score,
            isCorrect,
            explanation: 'Comentário sobre a sequência enviada.',
          },
          frozenAnswer: {
            kind: 'ordering',
            questionKey: ORDERING_QUESTION.key,
            orderedStepKeys: ['wash', 'cut', 'cook'],
          },
          isLastQuestion,
          handleContinue,
        }),
      )
      render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

      expect(screen.getAllByText(label).length).toBeGreaterThan(0)
      expect(screen.getByText(`${score}%`)).toBeVisible()
      expect(
        screen.getByText(/a nota final da Atividade será calculada após o envio/),
      ).toBeVisible()
      expect(screen.getByText('Comentário sobre a sequência enviada.')).toBeVisible()
      expect(screen.queryByRole('button', { name: /Mover para/ })).not.toBeInTheDocument()
      fireEvent.click(screen.getByRole('button', { name: action }))
      expect(handleContinue).toHaveBeenCalledOnce()
    },
  )

  it.each([
    { feedback: null, label: 'Tentar avaliação novamente' },
    { feedback: { status: 'inconclusive' as const, score: null }, label: 'Reverificar' },
  ])('keeps an unconfirmed order frozen and offers $label', ({ feedback, label }) => {
    const handleContinue = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: { ...ACTIVITY, questions: [ORDERING_QUESTION] },
        isMixedActivity: true,
        currentQuestion: ORDERING_QUESTION,
        currentOrderingOrder: ['cut', 'wash', 'cook'],
        frozenAnswer: {
          kind: 'ordering',
          questionKey: ORDERING_QUESTION.key,
          orderedStepKeys: ['cut', 'wash', 'cook'],
        },
        feedback,
        handleContinue,
        hasFeedbackError: feedback === null,
      }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Mover para cima: Cortar' })).toBeDisabled()
    if (feedback === null) {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Não foi possível avaliar. Tente novamente.',
      )
    } else {
      expect(
        screen.getByText(
          'Não foi possível concluir esta avaliação. Reavalie a mesma resposta.',
        ),
      ).toBeVisible()
      expect(screen.queryByText('Pontuação:')).not.toBeInTheDocument()
    }
    fireEvent.click(screen.getByRole('button', { name: label }))
    expect(handleContinue).toHaveBeenCalledOnce()
  })

  it('renders the image options and delegates the choice and the verification', () => {
    const handleToggleOptionMock = vi.fn()
    const handleContinueMock = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: {
          ...ACTIVITY,
          activityRevision: 'revision-1',
          questions: [IMAGE_QUESTION],
        },
        isMixedActivity: true,
        currentQuestion: IMAGE_QUESTION,
        feedback: null,
        isLastQuestion: false,
        selectedOptionKeys: ['opt-1'],
        handleToggleOption: handleToggleOptionMock,
        handleContinue: handleContinueMock,
      }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByText('escolha uma imagem')).toBeVisible()
    expect(screen.getByRole('radio', { name: 'Opção 1' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Opção 1' })).toHaveAccessibleDescription(
      'Fatias brancas e firmes.',
    )
    fireEvent.click(screen.getByRole('radio', { name: 'Opção 2' }))
    expect(handleToggleOptionMock).toHaveBeenCalledWith('opt-2')
    fireEvent.click(screen.getByRole('button', { name: 'Verificar' }))
    expect(handleContinueMock).toHaveBeenCalledOnce()
    expect(screen.queryByRole('region', { name: 'Resultado' })).not.toBeInTheDocument()
  })

  it.each([
    {
      isCorrect: true,
      title: 'Resposta correta',
      isLastQuestion: false,
      action: 'Próxima questão',
    },
    {
      isCorrect: false,
      title: 'Resposta incorreta',
      isLastQuestion: true,
      action: 'Enviar atividade',
    },
  ])(
    'locks the image choice after verifying and offers $action with the $title feedback',
    ({ isCorrect, title, isLastQuestion, action }) => {
      const handleContinueMock = vi.fn()
      useActivityPageMock.mockReturnValue(
        createControllerMock({
          activity: {
            ...ACTIVITY,
            activityRevision: 'revision-1',
            questions: [IMAGE_QUESTION],
          },
          isMixedActivity: true,
          currentQuestion: IMAGE_QUESTION,
          selectedOptionKeys: ['opt-3'],
          feedback: {
            status: 'conclusive',
            score: isCorrect ? 100 : 0,
            isCorrect,
            optionFeedback: 'Linha da imagem escolhida.',
            explanation: 'Explicação predefinida.',
          },
          frozenAnswer: {
            kind: 'image_choice',
            questionKey: IMAGE_QUESTION.key,
            selectedOptionKeys: ['opt-3'],
          },
          isLastQuestion,
          handleContinue: handleContinueMock,
        }),
      )
      render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

      for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled()
      expect(
        screen.getByRole('radio', { name: 'Opção 3' }).closest('label'),
      ).toHaveAttribute('data-tone', isCorrect ? 'correct' : 'incorrect')
      expect(screen.getByRole('heading', { name: title })).toBeVisible()
      expect(screen.getByText('Linha da imagem escolhida.')).toBeVisible()
      expect(screen.getByText('Explicação predefinida.')).toBeVisible()
      expect(screen.queryByRole('button', { name: 'Verificar' })).not.toBeInTheDocument()
      fireEvent.click(screen.getByRole('button', { name: action }))
      expect(handleContinueMock).toHaveBeenCalledOnce()
    },
  )

  it('keeps an unverified image choice frozen and offers to try the verification again', () => {
    const handleContinueMock = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: {
          ...ACTIVITY,
          activityRevision: 'revision-1',
          questions: [IMAGE_QUESTION],
        },
        isMixedActivity: true,
        currentQuestion: IMAGE_QUESTION,
        selectedOptionKeys: ['opt-2'],
        feedback: null,
        frozenAnswer: {
          kind: 'image_choice',
          questionKey: IMAGE_QUESTION.key,
          selectedOptionKeys: ['opt-2'],
        },
        hasFeedbackError: true,
        handleContinue: handleContinueMock,
      }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível avaliar. Tente novamente.',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Tentar avaliação novamente' }))
    expect(handleContinueMock).toHaveBeenCalledOnce()
  })

  it('announces loading without exposing stale question controls', () => {
    useActivityPageMock.mockReturnValue(createControllerMock({ isLoading: true }))
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
    expect(
      screen.getByRole('status', { name: 'Carregando Atividade...' }),
    ).toHaveAttribute('aria-busy', 'true')
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })

  it('renders private absence without a retry or activity content', () => {
    useActivityPageMock.mockReturnValue(createControllerMock({ isPrivateAbsence: true }))
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
    expect(
      screen.getByRole('heading', { name: 'Atividade não encontrada' }),
    ).toBeVisible()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it.each([{ isDiagnosticEntryRequired: true }, { currentQuestion: null }])(
    'waits without rendering controls when the route cannot expose a question: %j',
    (state) => {
      useActivityPageMock.mockReturnValue(createControllerMock(state))
      const { container } = render(
        <ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />,
      )
      expect(container).toBeEmptyDOMElement()
    },
  )

  it.each([{ isRecoverableError: true }, { activity: null }])(
    'offers retry for unavailable activity data: %j',
    (state) => {
      const handleRetryLoad = vi.fn()
      useActivityPageMock.mockReturnValue(
        createControllerMock({ ...state, handleRetryLoad }),
      )
      render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Não foi possível carregar esta Atividade',
      )
      fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
      expect(handleRetryLoad).toHaveBeenCalledOnce()
    },
  )

  it.each([false, true])(
    'recovers failed diagnostic evaluation when activity data is absent: pending=%s',
    (isRetryingDiagnostic) => {
      const handleRetryDiagnostic = vi.fn()
      useActivityPageMock.mockReturnValue(
        createControllerMock({
          activity: null,
          isDiagnosticProcessing: true,
          diagnosticStatus: 'failed',
          isRetryingDiagnostic,
          diagnosticRetryError: true,
          handleRetryDiagnostic,
        }),
      )
      render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
      expect(
        screen.getByText('A avaliação falhou no Shifu. Sua resposta foi preservada.'),
      ).toBeVisible()
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Não foi possível tentar novamente agora.',
      )
      const retry = screen.getByRole('button', {
        name: isRetryingDiagnostic ? 'Tentando novamente…' : 'Tentar avaliação novamente',
      })
      if (isRetryingDiagnostic) expect(retry).toBeDisabled()
      else {
        fireEvent.click(retry)
        expect(handleRetryDiagnostic).toHaveBeenCalledOnce()
      }
    },
  )

  it.each([false, true])(
    'retries consolidation and diagnostic status with activity present=%s',
    (hasActivity) => {
      const handleRetryDiagnosticCompletion = vi.fn()
      const handleRetryDiagnosticStatus = vi.fn()
      useActivityPageMock.mockReturnValue(
        createControllerMock({
          activity: hasActivity ? { ...ACTIVITY, isDiagnostic: true } : null,
          isDiagnosticProcessing: true,
          diagnosticCompletionError: true,
          hasDiagnosticStatusError: true,
          diagnosticRetryError: true,
          handleRetryDiagnosticCompletion,
          handleRetryDiagnosticStatus,
        }),
      )
      render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
      expect(screen.getByText('Não foi possível consolidar o resultado.')).toBeVisible()
      fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
      fireEvent.click(screen.getByRole('button', { name: 'Atualizar avaliação' }))
      expect(handleRetryDiagnosticCompletion).toHaveBeenCalledOnce()
      expect(handleRetryDiagnosticStatus).toHaveBeenCalledOnce()
      expect(screen.getByText('Não foi possível tentar novamente agora.')).toBeVisible()
    },
  )

  it('announces diagnostic consolidation and prevents further answers', () => {
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: { ...ACTIVITY, isDiagnostic: true },
        isDiagnosticProcessing: true,
        isCompletingDiagnostic: true,
      }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
    expect(screen.getByText('Consolidando o resultado…')).toBeVisible()
    expect(
      screen.getByRole('checkbox', { name: 'O laço executa três vezes.' }),
    ).toBeDisabled()
  })

  it('announces processing while diagnostic data is being restored', () => {
    useActivityPageMock.mockReturnValue(
      createControllerMock({ activity: null, isDiagnosticProcessing: true }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
    expect(screen.getByText('Avaliando o diagnóstico…')).toBeVisible()
  })

  it.each([
    { isAssessing: true, label: 'Avaliando questão…' },
    { isSubmitting: true, label: 'Enviando respostas…' },
    { isLastQuestion: false, label: 'Próxima questão' },
    { isMixedActivity: true, feedback: null, label: 'Avaliar resposta' },
    {
      isMixedActivity: true,
      feedback: null,
      frozenAnswer: { questionKey: 'question-1', selectedOptionKeys: ['a'] },
      hasFeedbackError: true,
      label: 'Tentar avaliação novamente',
    },
    {
      isMixedActivity: true,
      feedback: { status: 'inconclusive' as const, score: null },
      label: 'Reavaliar resposta',
    },
    { isMixedActivity: true, isLastQuestion: false, label: 'Próxima questão' },
  ])(
    'labels and delegates the current advancement state: $label',
    ({ label, ...state }) => {
      const handleContinue = vi.fn()
      const handleToggleOption = vi.fn()
      useActivityPageMock.mockReturnValue(
        createControllerMock({
          ...state,
          handleContinue,
          handleToggleOption,
          canContinue: true,
        }),
      )
      render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
      fireEvent.click(screen.getByRole('button', { name: label }))
      expect(handleContinue).toHaveBeenCalledOnce()
      if (state.hasFeedbackError)
        expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível avaliar.')
    },
  )

  it('delegates choice changes through the public checkbox control', () => {
    const handleToggleOption = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({ feedback: null, handleToggleOption }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
    fireEvent.click(screen.getByRole('checkbox', { name: 'A condição é reavaliada.' }))
    expect(handleToggleOption).toHaveBeenCalledWith('b')
  })

  it.each([
    {
      sequence: [{ competencyId: 'competency-test', activityId: 'activity-test' }],
      label: 'Enviar diagnóstico',
    },
    {
      sequence: [
        { competencyId: 'competency-test', activityId: 'activity-test' },
        { competencyId: 'other', activityId: 'next' },
      ],
      label: 'Próxima competência',
    },
    {
      sequence: [
        { competencyId: 'competency-test', activityId: 'activity-test' },
        { competencyId: 'competency-test', activityId: 'next' },
      ],
      label: 'Próxima questão',
    },
  ])(
    'uses the diagnostic sequence to label the next action: $label',
    ({ sequence, label }) => {
      setDiagnosticRun('goal-test', 'skill-test', 'run-test')
      setDiagnosticSequence('goal-test', 'skill-test', 'run-test', sequence)
      useActivityPageMock.mockReturnValue(
        createControllerMock({ activity: { ...ACTIVITY, isDiagnostic: true } }),
      )
      render(
        <ActivityPage
          goalId='goal-test'
          skillId='skill-test'
          competencyId='competency-test'
          activityId='activity-test'
          onNavigateToAttempt={vi.fn()}
          onUnsentAnswersChange={vi.fn()}
          onSessionExpired={vi.fn()}
        />,
      )
      expect(screen.getByRole('button', { name: label })).toBeEnabled()
    },
  )

  it('renders the activity hierarchy and selected question state', () => {
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByRole('heading', { name: 'Estruturas de repetição' })).toBeVisible()
    expect(
      screen.getByRole('heading', { name: 'Quais afirmações são verdadeiras?' }),
    ).toBeVisible()
    expect(
      screen.getByRole('checkbox', { name: 'O laço executa três vezes.' }),
    ).toBeChecked()
    expect(screen.getByRole('button', { name: 'Enviar respostas' })).toBeEnabled()
  })

  it('keeps the advance action disabled until the current answer is valid', () => {
    useActivityPageMock.mockReturnValue(
      createControllerMock({ canContinue: false, selectedOptionKeys: [] }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Enviar respostas' })).toBeDisabled()
  })

  it('shows diagnostic progress and submission without individual feedback', () => {
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: { ...ACTIVITY, isDiagnostic: true },
        feedback: { status: 'conclusive', score: 100 },
      }),
    )

    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByRole('heading', { level: 1, name: 'Diagnóstico' })).toBeVisible()
    expect(screen.queryByText('Questão 1 de 1')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('progressbar', { name: 'Progresso da Atividade' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Estruturas de repetição' }),
    ).toBeVisible()
    const prompt = screen.getByRole('heading', {
      name: 'Quais afirmações são verdadeiras?',
    })
    expect(prompt.closest('section')?.parentElement).toHaveClass(
      'border-control-border',
      'bg-card',
    )
    expect(
      screen.getByText(/resultado aparecerá apenas no resumo consolidado/i),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Próxima questão' })).toBeEnabled()
    expect(
      screen.queryByText(/100%|resposta correta|resposta incorreta/i),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Resultado da questão' }),
    ).not.toBeInTheDocument()
  })

  it('shows a distinct stale-run state and a recovery action', () => {
    const handleReturnToSkill = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: null,
        isInvalidated: true,
        handleReturnToSkill,
      }),
    )

    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(
      screen.getByRole('heading', { name: 'Este diagnóstico foi substituído' }),
    ).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Voltar à Habilidade' }))
    expect(handleReturnToSkill).toHaveBeenCalledOnce()
  })

  it('shows submission recovery while preserving the selected answer', () => {
    const handleContinueMock = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        handleContinue: handleContinueMock,
        hasSubmissionError: true,
        isSubmissionLocked: true,
      }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível enviar suas respostas.',
    )
    expect(
      screen.getByRole('checkbox', { name: 'O laço executa três vezes.' }),
    ).toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar enviar novamente' }))
    expect(handleContinueMock).toHaveBeenCalledOnce()
    expect(
      screen.getByRole('checkbox', { name: 'O laço executa três vezes.' }),
    ).toBeChecked()
  })

  it('keeps a submitted diagnostic on its Activity and retries its failed evaluation', () => {
    const handleRetryDiagnostic = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: { ...ACTIVITY, isDiagnostic: true },
        feedback: null,
        isDiagnosticProcessing: true,
        diagnosticStatus: 'failed',
        handleRetryDiagnostic,
      }),
    )

    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(
      screen.getByText('A avaliação falhou no Shifu. Sua resposta foi preservada.'),
    ).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Enviar respostas' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/nota|resposta correta|correção/i)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar avaliação novamente' }))
    expect(handleRetryDiagnostic).toHaveBeenCalledOnce()
  })

  it('keeps diagnostic choices visible but disabled during evaluation', () => {
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: { ...ACTIVITY, isDiagnostic: true },
        feedback: null,
        isDiagnosticProcessing: true,
      }),
    )

    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByText('Avaliando o diagnóstico…')).toBeVisible()
    expect(
      screen.getByRole('checkbox', { name: 'O laço executa três vezes.' }),
    ).toBeChecked()
    expect(
      screen.getByRole('checkbox', { name: 'O laço executa três vezes.' }),
    ).toBeDisabled()
    expect(
      screen.getByRole('checkbox', { name: 'A condição é reavaliada.' }),
    ).toBeDisabled()
  })

  it('disables the code question during diagnostic evaluation', () => {
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: { ...ACTIVITY, isDiagnostic: true },
        currentQuestion: CODE_QUESTION,
        feedback: null,
        isDiagnosticProcessing: true,
      }),
    )

    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByText('Avaliando o diagnóstico…')).toBeVisible()
    expect(vi.mocked(CodeQuestion).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({ disabled: true }),
    )
  })

  it('passes the route runner factory through to the code-question boundary', () => {
    const runnerFactory = vi.fn(() => ({}) as CodePracticeRunner)
    useActivityPageMock.mockReturnValue(
      createControllerMock({ currentQuestion: CODE_QUESTION, runnerFactory }),
    )

    render(
      <ActivityPage
        activity={ACTIVITY}
        onSubmit={vi.fn()}
        runnerFactory={runnerFactory}
      />,
    )

    expect(vi.mocked(CodeQuestion).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({ runnerFactory }),
    )
  })

  it('composes the HTML/CSS/JavaScript widget with the mixed Activity draft and assessment contracts', () => {
    const htmlCssJsRunnerFactory = vi.fn(() => ({}) as never)
    const activity = {
      ...ACTIVITY,
      activityRevision: 'revision-html',
      questions: [HTML_CSS_JS_QUESTION],
    }
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity,
        currentQuestion: HTML_CSS_JS_QUESTION,
        htmlCssJsRunnerFactory,
        isMixedActivity: true,
        feedback: null,
      }),
    )

    render(<ActivityPage activity={activity} onSubmit={vi.fn()} />)

    expect(screen.getByTestId('html-css-js-question')).toBeVisible()
    expect(vi.mocked(HtmlCssJsQuestion).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        question: HTML_CSS_JS_QUESTION,
        activityRevision: 'revision-html',
        runnerFactory: htmlCssJsRunnerFactory,
        draftStore: expect.any(Object),
        onAssess: expect.any(Function),
      }),
    )
  })

  it('keeps the code editor available after preliminary feedback', () => {
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        currentQuestion: CODE_QUESTION,
        isMixedActivity: true,
        frozenAnswer: {
          kind: 'javascript_stdin',
          questionKey: CODE_QUESTION.key,
          files: [{ path: 'index.js', content: 'console.log(1)' }],
        },
      }),
    )

    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(vi.mocked(CodeQuestion).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({ disabled: false }),
    )
  })

  it('shows criterion titles and styled levels in code feedback', () => {
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        currentQuestion: {
          ...CODE_QUESTION,
          criteria: [
            {
              key: 'function-signature',
              name: 'Assinatura da função',
              weightPercentage: 20,
            },
          ],
        },
        feedback: {
          status: 'conclusive',
          score: 75,
          criteria: [
            {
              key: 'function-signature',
              weightPercentage: 20,
              level: '75',
              commentId: 'needs-function-signature',
              comment: 'Defina classificarNumero(numero) corretamente.',
            },
          ],
        },
        isMixedActivity: true,
      }),
    )

    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByText('Assinatura da função')).toBeVisible()
    expect(screen.queryByText('function-signature')).not.toBeInTheDocument()
    expect(screen.getByText('Peso 20%')).toBeVisible()
    expect(screen.getByRole('status', { name: 'Nível 75 de 100' })).toHaveTextContent(
      '75/100',
    )
    expect(
      screen.getByText('Defina classificarNumero(numero) corretamente.'),
    ).toBeVisible()
  })
  it('renders React as read only after inconclusive feedback and delegates retry', () => {
    const question = {
      ...CODE_QUESTION,
      kind: 'react' as const,
      initialFiles: [{ path: 'src/App.tsx', content: 'initial', editable: true }],
      entrypoint: 'src/App.tsx',
      editablePaths: ['src/App.tsx'],
      additionalFilePolicy: null,
      criteria: [{ key: 'complete', name: 'Completude React', weightPercentage: 100 }],
    }
    const handleContinue = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: {
          ...ACTIVITY,
          activityRevision: 'react-revision',
          questions: [question],
        },
        currentQuestion: question,
        isMixedActivity: true,
        feedback: {
          status: 'inconclusive',
          score: null,
          submittedFiles: [{ path: 'src/App.tsx', content: 'server snapshot' }],
          criteria: [
            {
              key: 'complete',
              weightPercentage: 100,
              level: 'inconclusive',
              commentId: 'unknown',
              comment: 'Evidência insuficiente.',
            },
          ],
        },
        frozenAnswer: {
          kind: 'react',
          questionKey: question.key,
          files: [{ path: 'src/App.tsx', content: 'local frozen' }],
        },
        handleContinue,
      }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
    expect(screen.getByRole('textbox', { name: 'Editor React' })).toHaveAttribute(
      'readonly',
    )
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeDisabled()
    expect(
      screen.getByText(
        'Não foi possível concluir esta avaliação. Reavalie a mesma resposta.',
      ),
    ).toBeVisible()
    expect(screen.getAllByText('Completude React').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByText('Arquivos avaliados'))
    expect(screen.getByText('server snapshot')).toBeVisible()
    expect(screen.queryByText('local frozen')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reavaliar resposta' }))
    expect(handleContinue).toHaveBeenCalledOnce()
  })

  it('keeps HTML response frozen and retries the same answer after inconclusive feedback', () => {
    const handleContinue = vi.fn()
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        activity: {
          ...ACTIVITY,
          activityRevision: 'html-revision',
          questions: [HTML_CSS_JS_QUESTION],
        },
        currentQuestion: HTML_CSS_JS_QUESTION,
        isMixedActivity: true,
        feedback: {
          status: 'inconclusive',
          score: null,
          submittedFiles: [
            { path: 'index.html', content: '<main>server snapshot</main>' },
          ],
          criteria: [
            {
              key: 'semantic',
              weightPercentage: 100,
              level: 'inconclusive',
              commentId: 'unknown',
              comment: 'Evidência insuficiente.',
            },
          ],
        },
        frozenAnswer: {
          kind: 'html_css_js',
          questionKey: HTML_CSS_JS_QUESTION.key,
          files: [{ path: 'index.html', content: '<main>resposta congelada</main>' }],
        },
        handleContinue,
      }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(vi.mocked(HtmlCssJsQuestion).mock.lastCall?.[0]).toMatchObject({
      disabled: true,
    })
    expect(
      screen.getByText(
        'Não foi possível concluir esta avaliação. Reavalie a mesma resposta.',
      ),
    ).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Reavaliar resposta' }))
    expect(handleContinue).toHaveBeenCalledOnce()
  })

  it('shows frozen React source when preliminary feedback has no submitted file projection', () => {
    const question = {
      ...CODE_QUESTION,
      kind: 'react' as const,
      additionalFilePolicy: null,
    }
    useActivityPageMock.mockReturnValue(
      createControllerMock({
        currentQuestion: question,
        isMixedActivity: true,
        frozenAnswer: {
          kind: 'react',
          questionKey: question.key,
          files: [{ path: 'src/App.tsx', content: 'frozen response' }],
        },
        feedback: { status: 'conclusive', score: 75 },
      }),
    )
    render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)
    fireEvent.click(screen.getByText('Arquivos avaliados'))
    expect(screen.getByText('frozen response')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeDisabled()
  })
  describe('with a fill-in-the-blank question', () => {
    const fillQuestion = FillBlanksQuestionFaker.fake()
    const fillActivity: ChoiceActivityDetail = {
      ...ACTIVITY,
      activityRevision: 'revision-1',
      questions: [fillQuestion],
    }

    function renderFill(overrides: Partial<ActivityPageController> = {}) {
      useActivityPageMock.mockReturnValue(
        createControllerMock({
          activity: fillActivity,
          currentQuestion: fillQuestion,
          currentQuestionNumber: 1,
          feedback: null,
          fillBlanksPlacements: [],
          isLastQuestion: false,
          isMixedActivity: true,
          totalQuestions: 3,
          ...overrides,
        }),
      )
      return render(<ActivityPage activity={fillActivity} onSubmit={vi.fn()} />)
    }

    it('renders the blanks and the word bank and keeps the check disabled until the fill is complete', () => {
      renderFill({ canContinue: false })

      expect(screen.getByRole('button', { name: 'Lacuna 1: vazia' })).toBeVisible()
      expect(screen.getByRole('region', { name: 'Banco de palavras' })).toBeVisible()
      expect(screen.getByRole('button', { name: 'Avaliar resposta' })).toBeDisabled()
      expect(screen.queryByRole('radio')).toBeNull()
    })

    it('enables the check once every blank is filled and delegates it', () => {
      const handleContinue = vi.fn()
      renderFill({
        canContinue: true,
        fillBlanksPlacements: [
          { blankKey: 'b1', wordKey: 'w1' },
          { blankKey: 'b2', wordKey: 'w3' },
          { blankKey: 'b3', wordKey: 'w4' },
        ],
        handleContinue,
      })

      expect(screen.getByText('3 de 3 lacunas preenchidas')).toBeVisible()
      fireEvent.click(screen.getByRole('button', { name: 'Avaliar resposta' }))
      expect(handleContinue).toHaveBeenCalledOnce()
    })

    it('places a selected word through the real widget and reports the new placements', () => {
      const handleFillBlanksChange = vi.fn()
      renderFill({ handleFillBlanksChange })

      fireEvent.click(screen.getByRole('button', { name: 'goes' }))
      fireEvent.click(screen.getByRole('button', { name: 'Lacuna 1: vazia' }))

      expect(handleFillBlanksChange).toHaveBeenCalledWith([
        { blankKey: 'b1', wordKey: 'w1' },
      ])
    })

    it('locks the blanks and the bank while the question is being assessed or submitted', () => {
      renderFill({ isFillBlanksLocked: true })

      expect(screen.getByRole('button', { name: 'Lacuna 1: vazia' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'walks' })).toBeDisabled()
    })

    it.each([
      [100, 3, 'Resposta correta', '3 de 3 lacunas corretas'],
      [66.67, 2, 'Parcialmente correta', '2 de 3 lacunas corretas'],
      [0, 0, 'Resposta incorreta', '0 de 3 lacunas corretas'],
    ])(
      'shows the provisional result at %s with its label, count and explanation',
      (score, correctBlankCount, label, count) => {
        renderFill({
          feedback: {
            status: 'conclusive',
            score,
            explanation: 'Explicação predefinida da questão.',
            isCorrect: score === 100,
            correctBlankCount,
            blankCount: 3,
          },
          fillBlanksPlacements: [
            { blankKey: 'b1', wordKey: 'w1' },
            { blankKey: 'b2', wordKey: 'w3' },
            { blankKey: 'b3', wordKey: 'w4' },
          ],
        })

        const result = screen.getByRole('region', { name: 'Resultado' })
        expect(result).toHaveTextContent(label)
        expect(result).toHaveTextContent(count)
        expect(result).toHaveTextContent('Explicação predefinida da questão.')
        expect(result).not.toHaveTextContent('Arquivos avaliados')
        expect(screen.getByRole('button', { name: 'Próxima questão' })).toBeVisible()
      },
    )
  })

  describe('pair matching question', () => {
    const PAIR_QUESTION = {
      key: 'pairs-1',
      kind: 'pair_matching',
      prompt: 'Associe as palavras.',
      sourceLanguage: 'en',
      targetLanguage: 'pt-BR',
      words: [{ key: 'w0', text: 'dog' }],
      translations: [{ key: 't0', text: 'cachorro' }],
    } satisfies NonNullable<ActivityPageController['currentQuestion']>
    const PAIRS = [{ wordKey: 'w0', translationKey: 't0' }]

    it('renders the pair widget with the formed pairs and the change handler', () => {
      const handlePairMatchingAnswerChange = vi.fn()
      useActivityPageMock.mockReturnValue(
        createControllerMock({
          currentQuestion: PAIR_QUESTION,
          feedback: null,
          frozenAnswer: null,
          handlePairMatchingAnswerChange,
          isMixedActivity: true,
          pairMatchingPairs: PAIRS,
        }),
      )

      render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

      expect(screen.getByTestId('pair-matching-question')).toBeVisible()
      expect(vi.mocked(PairMatchingQuestion).mock.lastCall?.[0]).toMatchObject({
        disabled: false,
        onChange: handlePairMatchingAnswerChange,
        pairs: PAIRS,
        question: PAIR_QUESTION,
      })
      expect(screen.getByRole('button', { name: 'Avaliar resposta' })).toBeEnabled()
    })

    it('locks the widget and offers the next step after verification', () => {
      useActivityPageMock.mockReturnValue(
        createControllerMock({
          currentQuestion: PAIR_QUESTION,
          feedback: { status: 'conclusive', score: 100, outcome: 'full' },
          frozenAnswer: { kind: 'pair_matching', questionKey: 'pairs-1', pairs: PAIRS },
          isLastQuestion: false,
          isMixedActivity: true,
          pairMatchingPairs: PAIRS,
        }),
      )

      render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

      expect(vi.mocked(PairMatchingQuestion).mock.lastCall?.[0]).toMatchObject({
        disabled: true,
      })
      expect(screen.getByRole('button', { name: 'Próxima questão' })).toBeEnabled()
    })

    it('disables Evaluate while the pairs are incomplete', () => {
      useActivityPageMock.mockReturnValue(
        createControllerMock({
          canContinue: false,
          currentQuestion: PAIR_QUESTION,
          feedback: null,
          frozenAnswer: null,
          isMixedActivity: true,
          pairMatchingPairs: [],
        }),
      )

      render(<ActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

      expect(screen.getByRole('button', { name: 'Avaliar resposta' })).toBeDisabled()
    })
  })
})
