import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ChoiceActivityDetail } from '@/core/learning/choice-activity'
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
import { createReactDraftStoreMock } from './react-draft-store-mock'
import type { CodeEditorProps } from '@/ui/learning/widgets/components/code-editor'

vi.mock('../use-activity-page', () => ({
  useActivityPage: vi.fn(),
}))
vi.mock('../code-question', () => ({ CodeQuestion: vi.fn(() => null) }))
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
    currentQuestion: ACTIVITY.questions[0],
    currentQuestionIndex: 0,
    currentQuestionNumber: 1,
    handleContinue: vi.fn(),
    handleRetryLoad: vi.fn(),
    handleReturnToSkill: vi.fn(),
    handleToggleOption: vi.fn(),
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
})
