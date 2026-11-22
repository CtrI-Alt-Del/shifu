import type { ComponentProps } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SkillExperienceDetailFaker } from '@/core/learning/fakers'
import type { SkillExperienceDetail } from '@/core/learning/skill-experience'

import { SkillPage } from '..'
import { useSkillExperience } from '../use-skill-experience'
import { useSkillPage } from '../use-skill-page'

type LinkMockProps = Omit<ComponentProps<'a'>, 'href'> & {
  params?: Record<string, string>
  to: string
}

// Entrance motion and counters settle at once, so assertions see the final
// state; the shared components own their own animated cases.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, params, to, ...props }: LinkMockProps) => (
    <a data-params={JSON.stringify(params)} href={to} {...props}>
      {children}
    </a>
  ),
}))
vi.mock('../use-skill-page', () => ({ useSkillPage: vi.fn() }))
vi.mock('@/ui/learning/hooks/use-diagnostic-leave-guard', () => ({
  useDiagnosticLeaveGuard: vi.fn(),
}))
vi.mock('../use-skill-experience', () => ({ useSkillExperience: vi.fn() }))

const useSkillPageMock = vi.mocked(useSkillPage)
const useSkillExperienceMock = vi.mocked(useSkillExperience)
const IDS = {
  goalId: '01SHF000000000000000000001',
  skillId: '01SHF000000000000000000002',
  competencyId: '01SHF000000000000000000003',
  activityId: '01SHF000000000000000000004',
}

function experienceController(experience: SkillExperienceDetail | null = null) {
  return {
    experience,
    handleRetryEvaluation: vi.fn(),
    isExperienceLoading: false,
    isRetrying: false,
    isCompleting: false,
    completionError: false,
    diagnosticRunId: null,
    retryFailed: false,
  } as unknown as ReturnType<typeof useSkillExperience>
}

function settledDiagnostic(status: 'learning' | 'completed') {
  return {
    status,
    runState: 'settled' as const,
    readyToComplete: false,
    nextCompetencyId: null,
    nextActivityId: null,
    pendingAttemptId: null,
    pendingAttemptStatus: null,
    focusCompetencyId: null,
    competencies: [],
    initialOverallResult: 64,
    overallCoverageComplete: true,
    directCompletion: false,
  }
}

function controller(overrides: Partial<ReturnType<typeof useSkillPage>> = {}) {
  return {
    diagnostic: null,
    skillName: 'Lógica de programação',
    isLoading: false,
    isPrivateAbsence: false,
    isRecoverableError: false,
    isStarting: false,
    startError: null,
    isRetrying: false,
    retryError: false,
    isRemovalDialogOpen: false,
    isRemovingSkill: false,
    removeSkillError: null,
    handleStart: vi.fn(async () => {}),
    handleRetryDiagnostic: vi.fn(async () => {}),
    handleRetryCompletion: vi.fn(async () => {}),
    handleRetry: vi.fn(async () => ({}) as never),
    handleOpenRemovalDialog: vi.fn(),
    handleCancelRemoval: vi.fn(),
    handleConfirmRemoval: vi.fn(async () => {}),
    ...overrides,
  } as ReturnType<typeof useSkillPage>
}

describe('SkillPage', () => {
  beforeEach(() => {
    useSkillExperienceMock.mockReturnValue(experienceController())
  })
  afterEach(cleanup)

  it('shows a non-interactive Skill skeleton while the diagnostic loads', () => {
    useSkillPageMock.mockReturnValue(controller({ isLoading: true }))
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)

    const status = screen.getByRole('status')
    expect(status).toHaveTextContent('Carregando Habilidade...')
    expect(status.querySelector('[data-slot="skeleton"]')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Iniciar Habilidade' }),
    ).not.toBeInTheDocument()
  })

  it('starts an eligible Skill without exposing diagnostic scores', () => {
    const handleStart = vi.fn(async () => {})
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'not-started',
          runState: 'requires_entry',
          readyToComplete: false,
          nextCompetencyId: null,
          nextActivityId: null,
          pendingAttemptId: null,
          pendingAttemptStatus: null,
          focusCompetencyId: null,
          competencies: [],
          initialOverallResult: null,
          overallCoverageComplete: false,
          directCompletion: false,
        },
        handleStart,
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(screen.getByText(/resultado consolidado ao final/i)).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar Habilidade' }))
    expect(handleStart).toHaveBeenCalledOnce()
  })

  it('opens the destructive confirmation in a diagnostic state', async () => {
    const user = userEvent.setup()
    const handleOpenRemovalDialog = vi.fn()
    const diagnostic = {
      status: 'not-started' as const,
      runState: 'requires_entry' as const,
      readyToComplete: false,
      nextCompetencyId: null,
      nextActivityId: null,
      pendingAttemptId: null,
      pendingAttemptStatus: null,
      focusCompetencyId: null,
      competencies: [],
      initialOverallResult: null,
      overallCoverageComplete: false,
      directCompletion: false,
    }
    useSkillPageMock.mockReturnValue(controller({ diagnostic, handleOpenRemovalDialog }))
    const { rerender } = render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)

    await user.click(
      screen.getByRole('button', { name: 'Mais ações de Lógica de programação' }),
    )
    await user.click(screen.getByRole('menuitem', { name: 'Remover habilidade' }))
    expect(handleOpenRemovalDialog).toHaveBeenCalledOnce()

    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic,
        isRemovalDialogOpen: true,
        removeSkillError: 'Não foi possível remover a Habilidade. Tente novamente.',
      }),
    )
    rerender(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(screen.getByRole('heading', { name: 'Remover Habilidade?' })).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent('Tente novamente')
  })

  it('explains a Curriculum coverage gap at start without entering diagnosis', () => {
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'not-started',
          runState: 'requires_entry',
          readyToComplete: false,
          nextCompetencyId: null,
          nextActivityId: null,
          pendingAttemptId: null,
          pendingAttemptStatus: null,
          focusCompetencyId: null,
          competencies: [],
          initialOverallResult: null,
          overallCoverageComplete: false,
          directCompletion: false,
        },
        startError:
          'O Currículo desta Habilidade ainda não tem cobertura suficiente para iniciar o diagnóstico.',
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(screen.getByRole('alert')).toHaveTextContent('cobertura suficiente')
    expect(
      screen.queryByRole('link', { name: 'Próxima Atividade' }),
    ).not.toBeInTheDocument()
  })

  it('shows a brief automatic transition to the next diagnostic Activity without a pause action', () => {
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'diagnosing',
          runState: 'active',
          readyToComplete: false,
          nextCompetencyId: IDS.competencyId,
          nextActivityId: IDS.activityId,
          pendingAttemptId: null,
          pendingAttemptStatus: null,
          focusCompetencyId: null,
          competencies: [],
          initialOverallResult: null,
          overallCoverageComplete: false,
          directCompletion: false,
        },
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(screen.getByRole('status')).toHaveTextContent('Abrindo a próxima Atividade...')
    expect(
      screen.queryByRole('link', { name: 'Próxima Atividade' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText(/resposta correta|resposta incorreta|nota de/i),
    ).not.toBeInTheDocument()
  })

  it('opens the pending Activity without showing a Skill page pause', () => {
    useSkillPageMock.mockReturnValue(
      controller({
        diagnosticRunId: 'b2a3f497-7f4b-4d5e-8bc0-a984e6c04c98',
        diagnostic: {
          status: 'diagnosing',
          runState: 'active',
          readyToComplete: false,
          nextCompetencyId: IDS.competencyId,
          nextActivityId: IDS.activityId,
          pendingAttemptId: '01SHF000000000000000000005',
          pendingAttemptStatus: 'pending',
          focusCompetencyId: null,
          competencies: [],
          initialOverallResult: null,
          overallCoverageComplete: false,
          directCompletion: false,
        },
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)

    expect(screen.getByRole('status')).toHaveTextContent('Carregando')
    expect(
      screen.queryByRole('link', { name: 'Próxima Atividade' }),
    ).not.toBeInTheDocument()
  })

  it('offers a safe retry for a failed diagnostic evaluation without exposing its result', () => {
    const handleRetryDiagnostic = vi.fn(async () => {})
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'diagnosing',
          runState: 'active',
          readyToComplete: false,
          nextCompetencyId: IDS.competencyId,
          nextActivityId: IDS.activityId,
          pendingAttemptId: '01SHF000000000000000000005',
          pendingAttemptStatus: 'failed',
          focusCompetencyId: null,
          competencies: [],
          initialOverallResult: null,
          overallCoverageComplete: false,
          directCompletion: false,
        },
        handleRetryDiagnostic,
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(screen.getByText(/resposta enviada foi preservada/i)).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar avaliação novamente' }))
    expect(handleRetryDiagnostic).toHaveBeenCalledOnce()
    expect(
      screen.queryByRole('link', { name: 'Próxima Atividade' }),
    ).not.toBeInTheDocument()
  })

  it('shows only a consolidated Competency summary after diagnosis', () => {
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'learning',
          runState: 'settled',
          readyToComplete: false,
          nextCompetencyId: null,
          nextActivityId: null,
          pendingAttemptId: null,
          pendingAttemptStatus: null,
          focusCompetencyId: IDS.competencyId,
          competencies: [
            {
              competencyId: IDS.competencyId,
              competencyName: 'Sequências',
              position: 1,
              progress: 72,
              coverageComplete: true,
              status: 'proficient',
              isFocus: true,
              contentReleased: true,
            },
          ],
          initialOverallResult: 72,
          overallCoverageComplete: true,
          directCompletion: false,
        },
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(
      screen.getByRole('heading', { name: 'Seu ponto de partida por Competência' }),
    ).toBeVisible()
    expect(screen.getByText('72%')).toBeVisible()
    expect(screen.queryByText(/Evidências incompletas/)).not.toBeInTheDocument()
    expect(screen.queryByText(/resposta correta/i)).not.toBeInTheDocument()
  })
  it('renders the completed view with the preserved result and no recommendation for a completed Skill', () => {
    useSkillPageMock.mockReturnValue(
      controller({ diagnostic: settledDiagnostic('completed') }),
    )
    useSkillExperienceMock.mockReturnValue(
      experienceController(
        SkillExperienceDetailFaker.fake({
          goalId: IDS.goalId,
          skillId: IDS.skillId,
          skillName: 'Lógica de programação',
          skillStatus: 'completed',
          recommendation: null,
          completion: SkillExperienceDetailFaker.fakeCompletion(),
        }),
      ),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)

    expect(
      screen.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
    ).toBeVisible()
    expect(screen.getByText('Concluída')).toBeVisible()
    expect(screen.getByText('2 set → 13 set')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Prática de revisão' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Voltar ao Objetivo' })).toBeVisible()
    expect(screen.queryByText('Progresso demonstrado')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Ver diagnóstico consolidado' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/Continuar praticando|Praticar /)).not.toBeInTheDocument()
  })

  it('opens the Skill removal from the completed view', async () => {
    const user = userEvent.setup()
    const handleOpenRemovalDialog = vi.fn()
    useSkillPageMock.mockReturnValue(
      controller({ diagnostic: settledDiagnostic('completed'), handleOpenRemovalDialog }),
    )
    useSkillExperienceMock.mockReturnValue(
      experienceController(
        SkillExperienceDetailFaker.fake({
          goalId: IDS.goalId,
          skillId: IDS.skillId,
          skillName: 'Lógica de programação',
          skillStatus: 'completed',
          completion: SkillExperienceDetailFaker.fakeCompletion(),
        }),
      ),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)

    await user.click(
      screen.getByRole('button', { name: 'Mais ações de Lógica de programação' }),
    )
    await user.click(screen.getByRole('menuitem', { name: 'Remover habilidade' }))

    expect(handleOpenRemovalDialog).toHaveBeenCalledOnce()
  })

  it('keeps the learning experience, with its recommendation, for a Skill in learning', () => {
    useSkillPageMock.mockReturnValue(
      controller({ diagnostic: settledDiagnostic('learning') }),
    )
    useSkillExperienceMock.mockReturnValue(
      experienceController(
        SkillExperienceDetailFaker.fake({
          goalId: IDS.goalId,
          skillId: IDS.skillId,
          skillName: 'Lógica de programação',
          skillStatus: 'learning',
          overallResult: 72,
          completion: null,
        }),
      ),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)

    expect(screen.getByText('Progresso demonstrado')).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Ver diagnóstico consolidado' }),
    ).toBeVisible()
    expect(
      screen.queryByRole('region', { name: 'Prática de revisão' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Voltar ao Objetivo' }),
    ).not.toBeInTheDocument()
  })

  it('falls back to the learning experience when a completed Skill has no completion overview', () => {
    useSkillPageMock.mockReturnValue(
      controller({ diagnostic: settledDiagnostic('completed') }),
    )
    useSkillExperienceMock.mockReturnValue(
      experienceController(
        SkillExperienceDetailFaker.fake({
          goalId: IDS.goalId,
          skillId: IDS.skillId,
          skillName: 'Lógica de programação',
          skillStatus: 'completed',
          completion: null,
        }),
      ),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)

    expect(screen.getByText('Progresso demonstrado')).toBeVisible()
    expect(
      screen.queryByRole('region', { name: 'Prática de revisão' }),
    ).not.toBeInTheDocument()
  })
})
