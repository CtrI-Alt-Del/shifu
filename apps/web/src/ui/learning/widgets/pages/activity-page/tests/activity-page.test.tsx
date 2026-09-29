import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ChoiceActivityDetail } from '@/core/learning/choice-activity'
import type { CodePracticeRunner } from '@/core/learning/code-practice-runner'

import { ActivityPage } from '..'
import { CodeQuestion } from '../code-question'
import type { ActivityPageController } from '../use-activity-page'
import { useActivityPage } from '../use-activity-page'

vi.mock('../use-activity-page', () => ({
  useActivityPage: vi.fn(),
}))
vi.mock('../code-question', () => ({ CodeQuestion: vi.fn(() => null) }))

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

function createControllerMock(
  overrides: Partial<ActivityPageController> = {},
): ActivityPageController {
  return {
    activity: ACTIVITY,
    runnerFactory: undefined,
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
    vi.stubGlobal('matchMedia', () => ({ matches: false }))
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

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
})
