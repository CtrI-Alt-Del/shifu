import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  ChoiceActivityDetail,
  ChoiceAttemptDetail,
  CodeResultQuestion,
  PracticalPreparationQuestion,
  PracticalPreparationResultQuestion,
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
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
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
      name: 'Progresso demonstrado da Habilidade',
    })
    expect(progressHeading).toBeVisible()
    expect(progressHeading.closest('section')).toHaveTextContent(
      /Antes:\s*68%.*Agora:\s*67%/,
    )
    expect(
      screen.getByRole('progressbar', {
        name: 'Progresso demonstrado da Habilidade após a avaliação',
      }),
    ).toHaveAttribute('aria-valuetext', '67%')
    expect(
      screen
        .getByRole('progressbar', {
          name: 'Progresso demonstrado da Habilidade após a avaliação',
        })
        .querySelector('div'),
    ).toHaveStyle({ width: '67%' })
    expect(
      screen.getByText(
        'O progresso considera suas respostas nesta Atividade e as evidências anteriores. Não é a nota acima.',
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
    expect(screen.getByRole('link', { name: 'Ler material didático' })).toBeVisible()
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

    expect(screen.getByLabelText('Nota da Atividade 72,5 de 100')).toHaveTextContent(
      /^72,5\s*\/ 100/,
    )
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

  it('renders the reward slot as an opaque node between the header and the progress block', () => {
    const rewardBand = <div data-testid='stub-reward-band'>stub reward band</div>

    render(
      <ChoiceResultPage
        activity={ACTIVITY}
        attempt={COMPLETED_ATTEMPT}
        onRetryEvaluation={vi.fn()}
        rewardBand={rewardBand}
        state='result'
      />,
    )

    const band = screen.getByTestId('stub-reward-band')
    expect(band).toBeVisible()
    const header = screen.getByRole('heading', { name: 'Resultado da Atividade' })
    const progress = screen.getByRole('heading', {
      name: 'Progresso demonstrado da Habilidade',
    })
    expect(
      header.compareDocumentPosition(band) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      progress.compareDocumentPosition(band) & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy()
  })

  it('never renders the reward slot on a branch with no confirmed reward to show', () => {
    const rewardBand = <div data-testid='stub-reward-band'>stub reward band</div>

    const { rerender } = render(
      <ChoiceResultPage rewardBand={rewardBand} state='loading' />,
    )
    expect(screen.queryByTestId('stub-reward-band')).not.toBeInTheDocument()

    rerender(<ChoiceResultPage rewardBand={rewardBand} state='private-absence' />)
    expect(screen.queryByTestId('stub-reward-band')).not.toBeInTheDocument()

    rerender(
      <ChoiceResultPage onRetryLoad={vi.fn()} rewardBand={rewardBand} state='error' />,
    )
    expect(screen.queryByTestId('stub-reward-band')).not.toBeInTheDocument()

    const pendingAttempt: ChoiceAttemptDetail = {
      ...COMPLETED_ATTEMPT,
      status: 'pending',
      score: null,
      questions: undefined,
    }
    rerender(
      <ChoiceResultPage
        activity={ACTIVITY}
        attempt={pendingAttempt}
        onRetryEvaluation={vi.fn()}
        rewardBand={rewardBand}
        state='result'
      />,
    )
    expect(screen.queryByTestId('stub-reward-band')).not.toBeInTheDocument()

    const failedAttempt: ChoiceAttemptDetail = {
      ...COMPLETED_ATTEMPT,
      status: 'failed',
      retryAllowed: false,
      score: null,
      questions: undefined,
    }
    rerender(
      <ChoiceResultPage
        activity={ACTIVITY}
        attempt={failedAttempt}
        onRetryEvaluation={vi.fn()}
        rewardBand={rewardBand}
        state='result'
      />,
    )
    expect(screen.queryByTestId('stub-reward-band')).not.toBeInTheDocument()
  })

  describe('practical preparation', () => {
    const PRACTICAL_QUESTION: PracticalPreparationQuestion = {
      key: 'practice-1',
      kind: 'practical_preparation',
      prompt: 'Prepare legumes salteados.',
      guidance: ['Use fogo alto.'],
      references: [],
      difficulty: 'easy',
      records: [
        { key: 'cuts', label: 'Cortes', mustShow: 'Os cortes' },
        { key: 'dish', label: 'Prato final', mustShow: 'O prato' },
      ],
      criteria: [
        {
          key: 'cut',
          name: 'Regularidade dos cortes',
          description: 'Cortes',
          weight: 40,
        },
        { key: 'heat', name: 'Aplicação da técnica', description: 'Técnica', weight: 60 },
      ],
    }
    const PRACTICAL_ACTIVITY: ChoiceActivityDetail = {
      ...ACTIVITY,
      title: 'Legumes salteados',
      questions: [PRACTICAL_QUESTION],
    }
    const GRADED_QUESTION: PracticalPreparationResultQuestion = {
      key: 'practice-1',
      kind: 'practical_preparation',
      prompt: 'Prepare legumes salteados.',
      records: [
        { key: 'cuts', label: 'Cortes' },
        { key: 'dish', label: 'Prato final' },
      ],
      photos: [
        { recordKey: 'cuts', photoId: 'photo-cuts' },
        { recordKey: 'dish', photoId: 'photo-dish' },
      ],
      reflection: 'Usei fogo alto e pouco óleo.',
      criteria: [
        {
          key: 'cut',
          name: 'Regularidade dos cortes',
          weight: 40,
          level: 75,
          comment: 'Cortes quase uniformes.',
        },
        {
          key: 'heat',
          name: 'Aplicação da técnica',
          weight: 60,
          level: null,
          comment: 'Não foi possível observar o ponto.',
        },
      ],
      closedWithoutGrade: false,
      unassessableRecords: [],
      guidance: null,
    }
    const NO_GRADE_QUESTION: PracticalPreparationResultQuestion = {
      ...GRADED_QUESTION,
      criteria: [],
      closedWithoutGrade: true,
      unassessableRecords: [
        {
          key: 'dish',
          label: 'Prato final',
          comment: 'O prato não aparece inteiro na foto.',
        },
      ],
      guidance: 'Fotografe o prato inteiro com boa luz.',
    }
    const DETAIL_IDS = {
      goalId: '01SHF000000000000000000001',
      skillId: '01SHF000000000000000000002',
      competencyId: '01SHF000000000000000000003',
      activityId: '01SHF000000000000000000004',
    }

    function buildPhotoUrl(photoId: string) {
      return `/api/photos/${photoId}`
    }

    function renderAttempt(
      attempt: ChoiceAttemptDetail,
      props: {
        buildPracticePhotoUrl?: (photoId: string) => string
        detailIds?: {
          goalId: string
          skillId: string
          competencyId: string
          activityId?: string
        }
        onOpenRecommendation?: (recommendation: ActivityRecommendation) => void
        recommendation?: ActivityRecommendation | null
      } = {},
    ) {
      return render(
        <ChoiceResultPage
          activity={PRACTICAL_ACTIVITY}
          attempt={attempt}
          buildPracticePhotoUrl={buildPhotoUrl}
          detailIds={DETAIL_IDS}
          onRetryEvaluation={vi.fn()}
          state='result'
          {...props}
        />,
      )
    }

    it('shows the Curriculum brief with weighted criteria beside the attempt card', () => {
      renderAttempt({
        ...COMPLETED_ATTEMPT,
        status: 'pending',
        score: null,
        questions: undefined,
      })

      expect(screen.getByText('Prepare legumes salteados.')).toBeVisible()
      expect(screen.getByText('Use fogo alto.')).toBeVisible()
      expect(screen.getByText('Regularidade dos cortes')).toBeVisible()
      expect(screen.getByText('Peso 40%')).toBeVisible()
    })

    it('keeps an evaluation in progress distinct from a score and from no grade', () => {
      renderAttempt({
        ...COMPLETED_ATTEMPT,
        status: 'pending',
        score: null,
        questions: undefined,
      })

      expect(
        screen.getByRole('heading', { name: 'Avaliação em andamento' }),
      ).toBeVisible()
      expect(screen.getByRole('status')).toHaveTextContent('Tentativa enviada')
      expect(screen.getByText('Você pode continuar estudando')).toBeVisible()
      expect(screen.getByRole('link', { name: 'Voltar à Habilidade' })).toBeVisible()
      expect(screen.queryByText(/sem nota/)).not.toBeInTheDocument()
      expect(screen.queryByText('/ 100')).not.toBeInTheDocument()
    })

    it('shows a recoverable failure that keeps the photos and retries the same attempt', () => {
      const attempt: ChoiceAttemptDetail = {
        ...COMPLETED_ATTEMPT,
        status: 'failed',
        retryAllowed: true,
        failureMessage: 'A avaliação foi interrompida.',
        score: null,
        questions: [GRADED_QUESTION],
      }
      const handleRetryEvaluationMock = vi.fn()
      useChoiceResultPageMock.mockReturnValue(
        createControllerMock({
          attempt,
          canRetry: true,
          handleRetryEvaluation: handleRetryEvaluationMock,
        }),
      )
      renderAttempt(attempt)

      expect(
        screen.getByRole('heading', { name: 'A avaliação não pôde terminar' }),
      ).toBeVisible()
      expect(screen.getByRole('alert')).toHaveTextContent('Avaliação pendente')
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Sua tentativa e suas fotos estão preservadas.',
      )
      expect(screen.getByText('A avaliação foi interrompida.')).toBeVisible()
      expect(screen.getByAltText('Foto do registro: Cortes')).toBeVisible()
      fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

      expect(handleRetryEvaluationMock).toHaveBeenCalledOnce()
    })

    it('disables the retry while it restarts and reports a failed restart', () => {
      const attempt: ChoiceAttemptDetail = {
        ...COMPLETED_ATTEMPT,
        status: 'failed',
        retryAllowed: true,
        score: null,
        questions: undefined,
      }
      useChoiceResultPageMock.mockReturnValue(
        createControllerMock({
          attempt,
          canRetry: false,
          isRetrying: true,
          hasRetryError: true,
        }),
      )
      renderAttempt(attempt)

      expect(
        screen.getByRole('button', { name: 'Reiniciando avaliação…' }),
      ).toBeDisabled()
      expect(
        screen.getByText('Não foi possível reiniciar agora. Tente novamente.'),
      ).toBeVisible()
    })

    it('hides the retry when the failure cannot be retried', () => {
      const attempt: ChoiceAttemptDetail = {
        ...COMPLETED_ATTEMPT,
        status: 'failed',
        retryAllowed: false,
        score: null,
        questions: undefined,
      }
      renderAttempt(attempt)

      expect(
        screen.queryByRole('button', { name: /Tentar novamente/ }),
      ).not.toBeInTheDocument()
    })

    it('shows a closed attempt as without grade with its improvement records and two actions', () => {
      renderAttempt({
        ...COMPLETED_ATTEMPT,
        status: 'closed_without_grade',
        score: null,
        progressBefore: null,
        progressAfter: null,
        questions: [NO_GRADE_QUESTION],
      })

      expect(
        screen.getByRole('heading', { name: 'Não foi possível avaliar estas fotos' }),
      ).toBeVisible()
      expect(screen.getByText('Tentativa encerrada · sem nota')).toBeVisible()
      expect(screen.getByText('O que ajustar na próxima tentativa')).toBeVisible()
      expect(screen.getByText('Registros a melhorar')).toBeVisible()
      expect(screen.getByText('O prato não aparece inteiro na foto.')).toBeVisible()
      expect(screen.getByText('Fotografe o prato inteiro com boa luz.')).toBeVisible()
      expect(screen.queryByText('/ 100')).not.toBeInTheDocument()
      expect(screen.queryByText(/Nota da Atividade/)).not.toBeInTheDocument()
      expect(screen.queryByText('Avaliação em andamento')).not.toBeInTheDocument()
      const newAttempt = screen.getByRole('link', { name: 'Iniciar nova tentativa' })
      expect(newAttempt).toHaveAttribute(
        'href',
        '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId',
      )
      expect(JSON.parse(newAttempt.getAttribute('data-params') ?? '{}')).toEqual(
        DETAIL_IDS,
      )
      const back = screen.getByRole('link', { name: 'Voltar à Habilidade' })
      expect(back).toHaveAttribute('href', '/learning/goals/$goalId/skills/$skillId')
      expect(JSON.parse(back.getAttribute('data-params') ?? '{}')).toEqual({
        goalId: DETAIL_IDS.goalId,
        skillId: DETAIL_IDS.skillId,
      })
    })

    it('keeps the photos and the reflection of a no-grade attempt read only', () => {
      renderAttempt({
        ...COMPLETED_ATTEMPT,
        status: 'closed_without_grade',
        score: null,
        questions: [NO_GRADE_QUESTION],
      })

      expect(screen.getByAltText('Foto do registro: Cortes')).toHaveAttribute(
        'src',
        '/api/photos/photo-cuts',
      )
      expect(screen.getByAltText('Foto do registro: Prato final')).toBeVisible()
      expect(screen.getByText('Resposta enviada · somente leitura')).toBeVisible()
      expect(screen.getByText('Usei fogo alto e pouco óleo.')).toBeVisible()
      expect(screen.getByText('Relato escrito por você · somente leitura')).toBeVisible()
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
      expect(
        screen.queryByRole('button', { name: /Remover|Trocar/ }),
      ).not.toBeInTheDocument()
    })

    it('does not offer a new attempt link when the Activity identity is unknown', () => {
      renderAttempt(
        {
          ...COMPLETED_ATTEMPT,
          status: 'closed_without_grade',
          score: null,
          questions: [NO_GRADE_QUESTION],
        },
        {
          buildPracticePhotoUrl: undefined,
          detailIds: {
            goalId: DETAIL_IDS.goalId,
            skillId: DETAIL_IDS.skillId,
            competencyId: DETAIL_IDS.competencyId,
          },
        },
      )

      expect(
        screen.queryByRole('link', { name: 'Iniciar nova tentativa' }),
      ).not.toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Voltar à Habilidade' })).toBeVisible()
      expect(screen.getAllByText('Foto indisponível')).toHaveLength(2)
    })

    it('shows a completed result with each criterion weight, level and preset comment', () => {
      renderAttempt({ ...COMPLETED_ATTEMPT, score: 45, questions: [GRADED_QUESTION] })

      expect(screen.getByRole('heading', { name: 'Atividade avaliada' })).toBeVisible()
      expect(screen.getByLabelText('Nota da Atividade 45 de 100')).toBeVisible()
      expect(screen.getByText('75 / 100')).toBeVisible()
      expect(screen.getByText('Cortes quase uniformes.')).toBeVisible()
      expect(screen.getByText('Sem nível')).toBeVisible()
      expect(screen.getByText('Não foi possível observar o ponto.')).toBeVisible()
      expect(screen.getAllByText('Peso 60%').length).toBeGreaterThan(0)
      expect(screen.getByText('Seu relato')).toBeVisible()
      expect(
        screen.getByText(
          'O resultado será considerado no progresso da Competência. A reflexão não entra na nota.',
        ),
      ).toBeVisible()
      expect(
        screen.queryByRole('link', { name: 'Iniciar nova tentativa' }),
      ).not.toBeInTheDocument()
      expect(
        screen.getByRole('link', { name: 'Voltar para a Competência' }),
      ).toBeVisible()
    })

    it('opens the recommended next Activity from a completed result', () => {
      const onOpenRecommendationMock = vi.fn()
      renderAttempt(
        { ...COMPLETED_ATTEMPT, score: 45, questions: [GRADED_QUESTION] },
        {
          onOpenRecommendation: onOpenRecommendationMock,
          recommendation: RECOMMENDATION,
        },
      )

      fireEvent.click(screen.getByRole('button', { name: 'Próxima Atividade' }))

      expect(onOpenRecommendationMock).toHaveBeenCalledWith(RECOMMENDATION)
    })

    it('omits the reflection section when the learner wrote none', () => {
      renderAttempt({
        ...COMPLETED_ATTEMPT,
        score: 45,
        questions: [{ ...GRADED_QUESTION, reflection: '' }],
      })

      expect(screen.queryByText('Seu relato')).not.toBeInTheDocument()
    })
  })
})
