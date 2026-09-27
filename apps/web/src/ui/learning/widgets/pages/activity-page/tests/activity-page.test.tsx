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
    handleToggleOption: vi.fn(),
    hasSubmissionError: false,
    hasUnsentAnswers: true,
    isSubmissionLocked: false,
    isLastQuestion: true,
    isLoading: false,
    isPrivateAbsence: false,
    isRecoverableError: false,
    isSubmitting: false,
    selectedOptionKeys: ['a'],
    totalQuestions: 1,
    ...overrides,
  }
}

describe('ActivityPage', () => {
  beforeEach(() => {
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
