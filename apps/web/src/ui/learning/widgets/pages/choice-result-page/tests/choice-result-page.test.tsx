import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  ChoiceActivityDetail,
  ChoiceAttemptDetail,
  CodeResultQuestion,
} from '@/core/learning/choice-activity'
import type {
  ActivityRecommendation,
  AvailableCompetencyDetail,
} from '@/core/learning/competency-detail'

import { ChoiceResultPage } from '..'
import type { ChoiceResultPageController } from '../use-choice-result-page'
import { useChoiceResultPage } from '../use-choice-result-page'

vi.mock('../use-choice-result-page', () => ({
  useChoiceResultPage: vi.fn(),
}))

type LinkMockProps = Omit<ComponentProps<'a'>, 'href'> & {
  params?: Record<string, string>
  to: string
}

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, params, to, ...props }: LinkMockProps) => (
    <a data-params={JSON.stringify(params)} href={to} {...props}>
      {children}
    </a>
  ),
}))

const useChoiceResultPageMock = vi.mocked(useChoiceResultPage)

const ACTIVITY: ChoiceActivityDetail = {
  activityId: 'activity-1',
  title: 'Estruturas de repetição',
  difficulty: 'medium',
  canSubmit: true,
  latestAttemptId: 'attempt-1',
  unresolvedAttemptId: null,
  questions: [
    {
      key: 'question-1',
      kind: 'single_choice',
      prompt: 'Qual valor?',
      options: [
        { key: 'correct', text: '5' },
        { key: 'selected', text: '0' },
      ],
    },
  ],
}

const COMPLETED_ATTEMPT: ChoiceAttemptDetail = {
  attemptId: 'attempt-1',
  activityId: 'activity-1',
  status: 'completed',
  submittedAt: '2026-09-23T12:00:00Z',
  retryAllowed: false,
  score: 0,
  progressBefore: 68,
  progressAfter: 67,
  statusBefore: 'developing',
  statusAfter: 'developing',
  questions: [
    {
      key: 'question-1',
      prompt: 'Qual valor?',
      submittedOptionKeys: ['selected'],
      score: 0,
      isCorrect: false,
      explanation: 'Revise a condição do laço.',
    },
  ],
}

const RECOMMENDATION: ActivityRecommendation = {
  competencyId: 'competency-1',
  activityId: 'activity-2',
  difficulty: 'easy',
  type: 'reinforcement',
}

const ADAPTIVE_DETAIL: AvailableCompetencyDetail = {
  availability: 'available',
  goalId: '01SHF000000000000000000001',
  skillId: '01SHF000000000000000000002',
  skillName: 'Lógica',
  competencyId: '01SHF000000000000000000003',
  competencyName: 'Repetição',
  progress: 42,
  status: 'developing',
  isFocus: true,
  focusReturned: false,
  focusCompetencyId: '01SHF000000000000000000003',
  focusCompetencyName: 'Repetição',
  items: [],
  recommendation: null,
  coverageComplete: false,
  verificationCause: null,
  adaptive: {
    targetConceptId: '01SHF000000000000000000004',
    targetConceptName: 'Laços',
    originalTargetConceptId: '01SHF000000000000000000004',
    originalTargetConceptName: 'Laços',
    recommendedCompetencyId: '01SHF000000000000000000003',
    materialCompetencyId: '01SHF000000000000000000003',
    reason: 'coverage',
    difficulty: 'easy',
    activityId: '01SHF000000000000000000005',
    materialId: '01SHF000000000000000000006',
    materialIsOptional: true,
    gap: null,
  },
}

function createControllerMock(
  overrides: Partial<ChoiceResultPageController> = {},
): ChoiceResultPageController {
  return {
    attempt: COMPLETED_ATTEMPT,
    canRetry: false,
    handleRetryEvaluation: vi.fn(),
    handleRetryLoad: vi.fn(),
    hasRetryError: false,
    isRetrying: false,
    pageState: 'result',
    renderProps: {
      state: 'result',
      activity: ACTIVITY,
      attempt: COMPLETED_ATTEMPT,
      onRetryEvaluation: vi.fn(),
    },
    ...overrides,
  }
}

describe('ChoiceResultPage', () => {
  beforeEach(() => useChoiceResultPageMock.mockReturnValue(createControllerMock()))
  afterEach(cleanup)

  it('announces loading and does not imply a score', () => {
    useChoiceResultPageMock.mockReturnValue(
      createControllerMock({ pageState: 'loading', attempt: null }),
    )
    render(<ChoiceResultPage state='loading' />)

    expect(
      screen.getByRole('status', { name: 'Carregando resultado da Atividade...' }),
    ).toBeVisible()
    expect(screen.queryByText('/ 100')).not.toBeInTheDocument()
  })

  it('renders a generic private absence and a recoverable load failure', () => {
    useChoiceResultPageMock.mockReturnValue(
      createControllerMock({ pageState: 'private-absence', attempt: null }),
    )
    const { rerender } = render(<ChoiceResultPage state='private-absence' />)
    expect(
      screen.getByRole('heading', { name: 'Resultado não encontrado' }),
    ).toBeVisible()

    const onRetryLoadMock = vi.fn()
    useChoiceResultPageMock.mockReturnValue(
      createControllerMock({ pageState: 'error', attempt: null }),
    )
    rerender(<ChoiceResultPage onRetryLoad={onRetryLoadMock} state='error' />)
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(onRetryLoadMock).toHaveBeenCalledOnce()
  })

  it('keeps pending without a score or retry action', () => {
    const attempt: ChoiceAttemptDetail = {
      ...COMPLETED_ATTEMPT,
      status: 'pending',
      score: null,
      questions: undefined,
    }
    render(
      <ChoiceResultPage
        activity={ACTIVITY}
        attempt={attempt}
        onRetryEvaluation={vi.fn()}
        state='result'
      />,
    )

    expect(screen.getByRole('status')).toHaveTextContent(
      'Estamos avaliando suas respostas.',
    )
    const pendingHeading = screen.getByRole('heading', {
      name: 'Avaliação em andamento',
    })
    expect(pendingHeading).toBeVisible()
    expect(
      screen.getByText('Você pode sair; o resultado ficará disponível aqui.'),
    ).toBeVisible()
    expect(screen.queryByText('/ 100')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Tentar novamente' }),
    ).not.toBeInTheDocument()
  })

  it('offers a retry only for an allowed failure and preserves saved answers', () => {
    const attempt: ChoiceAttemptDetail = {
      ...COMPLETED_ATTEMPT,
      status: 'failed',
      retryAllowed: true,
      failureMessage: 'A avaliação foi interrompida.',
      score: null,
      questions: undefined,
    }
    const onRetryEvaluationMock = vi.fn().mockResolvedValue(undefined)
    const handleRetryEvaluationMock = vi.fn()
    useChoiceResultPageMock.mockReturnValue(
      createControllerMock({
        canRetry: true,
        attempt,
        handleRetryEvaluation: handleRetryEvaluationMock,
        pageState: 'result',
      }),
    )
    render(
      <ChoiceResultPage
        activity={ACTIVITY}
        attempt={attempt}
        onRetryEvaluation={onRetryEvaluationMock}
        state='result'
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Suas respostas continuam salvas')
    expect(screen.getByText('A avaliação foi interrompida.')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(handleRetryEvaluationMock).toHaveBeenCalledOnce()
    expect(screen.getByText('Suas respostas continuam salvas')).toBeVisible()
  })

  it('shows a complete score, progress regression, details and recommended next action', () => {
    const onOpenRecommendationMock = vi.fn()
    render(
      <ChoiceResultPage
        activity={ACTIVITY}
        attempt={COMPLETED_ATTEMPT}
        detailIds={{
          goalId: ADAPTIVE_DETAIL.goalId,
          skillId: ADAPTIVE_DETAIL.skillId,
          competencyId: ADAPTIVE_DETAIL.competencyId,
        }}
        onRetryEvaluation={vi.fn()}
        onOpenRecommendation={onOpenRecommendationMock}
        recommendation={RECOMMENDATION}
        state='result'
      />,
    )

    expect(screen.getByRole('heading', { name: 'Resultado da Atividade' })).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Voltar para a Competência' }),
    ).toHaveAttribute(
      'data-params',
      JSON.stringify({
        goalId: ADAPTIVE_DETAIL.goalId,
        skillId: ADAPTIVE_DETAIL.skillId,
        competencyId: ADAPTIVE_DETAIL.competencyId,
      }),
    )
    expect(
      screen.queryByRole('button', { name: 'Voltar para Atividade' }),
    ).not.toBeInTheDocument()
    expect(screen.getByLabelText('Nota da Atividade 0 de 100')).toBeVisible()
    const progressHeading = screen.getByRole('heading', {
      name: 'Progresso da Competência',
    })
    expect(progressHeading).toBeVisible()
    expect(progressHeading.closest('section')).toHaveTextContent(
      /Antes:\s*68%.*Agora:\s*67%/,
    )
    expect(
      screen.getByRole('progressbar', {
        name: 'Domínio estimado da Competência após a avaliação',
      }),
    ).toHaveAttribute('aria-valuetext', '67%')
    expect(
      screen.getByText(
        'A estimativa considera suas respostas nesta Atividade e, quando houver, evidências anteriores. Não é a nota acima.',
      ),
    ).toBeVisible()
    fireEvent.click(screen.getByText(/Questão 1 · escolha única/))
    expect(screen.getByText('Revise a condição do laço.')).toBeVisible()
    expect(screen.getByText('Atividade de reforço recomendada')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Próxima Atividade' }))
    expect(onOpenRecommendationMock).toHaveBeenCalledWith(RECOMMENDATION)
  })

  it('shows the adaptive Concept decision after a completed learning result', () => {
    render(
      <ChoiceResultPage
        activity={ACTIVITY}
        adaptiveDetail={ADAPTIVE_DETAIL}
        attempt={COMPLETED_ATTEMPT}
        onRetryEvaluation={vi.fn()}
        recommendation={RECOMMENDATION}
        state='result'
      />,
    )

    expect(screen.getByLabelText('Nota da Atividade 0 de 100')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Laços' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Ler Material opcional' })).toBeVisible()
    expect(
      screen.getByRole('link', { name: /Abrir Atividade recomendada/ }),
    ).toBeVisible()
    expect(screen.queryByText('Atividade de reforço recomendada')).not.toBeInTheDocument()
  })

  it('keeps the result visible and links to Competency if the adaptive detail cannot load', () => {
    render(
      <ChoiceResultPage
        activity={ACTIVITY}
        adaptiveLoadError
        attempt={COMPLETED_ATTEMPT}
        detailIds={{
          goalId: ADAPTIVE_DETAIL.goalId,
          skillId: ADAPTIVE_DETAIL.skillId,
          competencyId: ADAPTIVE_DETAIL.competencyId,
        }}
        onRetryEvaluation={vi.fn()}
        recommendation={RECOMMENDATION}
        state='result'
      />,
    )
    expect(screen.getByLabelText('Nota da Atividade 0 de 100')).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Ver Competência e próxima recomendação' }),
    ).toBeVisible()
    expect(screen.queryByText('Atividade de reforço recomendada')).not.toBeInTheDocument()
  })

  it('formats persisted integer and fractional Activity scores compactly', () => {
    const integerAttempt: ChoiceAttemptDetail = {
      ...COMPLETED_ATTEMPT,
      score: '100.00' as unknown as number,
    }
    const { rerender } = render(
      <ChoiceResultPage
        activity={ACTIVITY}
        attempt={integerAttempt}
        onRetryEvaluation={vi.fn()}
        state='result'
      />,
    )

    expect(screen.getByLabelText('Nota da Atividade 100 de 100')).toBeVisible()

    const fractionalAttempt: ChoiceAttemptDetail = {
      ...COMPLETED_ATTEMPT,
      score: '72.50' as unknown as number,
    }
    rerender(
      <ChoiceResultPage
        activity={ACTIVITY}
        attempt={fractionalAttempt}
        onRetryEvaluation={vi.fn()}
        state='result'
      />,
    )

    expect(screen.getByLabelText('Nota da Atividade 72,5 de 100')).toBeVisible()
  })

  it('keeps mixed result summaries independent and supports opening choice and code details', () => {
    const codeQuestion = {
      key: 'code-question-1',
      kind: 'javascript_stdin' as const,
      prompt: 'Dobre o número recebido.',
      initialFiles: [{ path: 'main.js', content: '', editable: true }],
      entrypoint: 'main.js',
      editablePaths: ['main.js'],
      fixedDependencies: [],
      permittedCommands: [],
      criteria: [{ key: 'logic', name: 'Lógica', weightPercentage: 100 }],
    }
    const mixedActivity: ChoiceActivityDetail = {
      ...ACTIVITY,
      questions: [ACTIVITY.questions[0], codeQuestion],
    }
    const codeResult: CodeResultQuestion = {
      key: codeQuestion.key,
      kind: 'javascript_stdin',
      prompt: codeQuestion.prompt,
      score: 75,
      submittedFiles: [{ path: 'main.js', content: 'console.log(2 * input)' }],
      criterionResults: [
        {
          key: 'logic',
          weightPercentage: 100,
          level: 75,
          commentId: 'comment-logic',
          comment: 'A lógica atende ao caso principal.',
        },
      ],
      conceptObservations: [],
    }
    const mixedAttempt: ChoiceAttemptDetail = {
      ...COMPLETED_ATTEMPT,
      questions: [...(COMPLETED_ATTEMPT.questions ?? []), codeResult],
    }

    render(
      <ChoiceResultPage
        activity={mixedActivity}
        attempt={mixedAttempt}
        onRetryEvaluation={vi.fn()}
        state='result'
      />,
    )

    expect(screen.getByText(/Questão 1 · escolha única/)).toBeVisible()
    expect(screen.getByText(/Questão 2 · JavaScript · entrada padrão/)).toBeVisible()
    expect(screen.queryByText('Revise a condição do laço.')).not.toBeVisible()
    expect(screen.queryByText('A lógica atende ao caso principal.')).not.toBeVisible()

    fireEvent.click(screen.getByText(/Questão 1 · escolha única/))
    fireEvent.click(screen.getByText(/Questão 2 · JavaScript · entrada padrão/))

    expect(screen.getByText('Revise a condição do laço.')).toBeVisible()
    expect(screen.getByText('A lógica atende ao caso principal.')).toBeVisible()
    expect(screen.getByText('Lógica · peso 100% · nível 75')).toBeVisible()
  })
})
