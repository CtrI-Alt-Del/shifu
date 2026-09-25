import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ChoiceActivityDetail } from '@/core/learning/choice-activity'

import { ChoiceActivityPage } from '..'
import type { ChoiceActivityPageController } from '../use-choice-activity-page'
import { useChoiceActivityPage } from '../use-choice-activity-page'

vi.mock('../use-choice-activity-page', () => ({
  useChoiceActivityPage: vi.fn(),
}))

const useChoiceActivityPageMock = vi.mocked(useChoiceActivityPage)

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

function createControllerMock(
  overrides: Partial<ChoiceActivityPageController> = {},
): ChoiceActivityPageController {
  return {
    activity: ACTIVITY,
    canContinue: true,
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

describe('ChoiceActivityPage', () => {
  beforeEach(() => {
    useChoiceActivityPageMock.mockReturnValue(createControllerMock())
  })

  afterEach(cleanup)

  it('renders the activity hierarchy and selected question state', () => {
    render(<ChoiceActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

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
    useChoiceActivityPageMock.mockReturnValue(
      createControllerMock({ canContinue: false, selectedOptionKeys: [] }),
    )
    render(<ChoiceActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Enviar respostas' })).toBeDisabled()
  })

  it('shows submission recovery while preserving the selected answer', () => {
    const handleContinueMock = vi.fn()
    useChoiceActivityPageMock.mockReturnValue(
      createControllerMock({
        handleContinue: handleContinueMock,
        hasSubmissionError: true,
        isSubmissionLocked: true,
      }),
    )
    render(<ChoiceActivityPage activity={ACTIVITY} onSubmit={vi.fn()} />)

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
})
