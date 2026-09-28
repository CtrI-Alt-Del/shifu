import type { ComponentProps } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SkillPage } from '..'
import { useSkillPage } from '../use-skill-page'

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
vi.mock('../use-skill-page', () => ({ useSkillPage: vi.fn() }))
vi.mock('@/ui/learning/hooks/use-diagnostic-leave-guard', () => ({
  useDiagnosticLeaveGuard: vi.fn(),
}))
vi.mock('../use-skill-experience', () => ({
  useSkillExperience: () => ({
    experience: null,
    handleRetryEvaluation: vi.fn(),
    isExperienceLoading: false,
    isRetrying: false,
    isCompleting: false,
    completionError: false,
    diagnosticRunId: null,
    retryFailed: false,
  }),
}))

const useSkillPageMock = vi.mocked(useSkillPage)
const IDS = {
  goalId: '01SHF000000000000000000001',
  skillId: '01SHF000000000000000000002',
  competencyId: '01SHF000000000000000000003',
  activityId: '01SHF000000000000000000004',
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
})
