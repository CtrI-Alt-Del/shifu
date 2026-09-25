import type { ComponentProps } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
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
    handleStart: vi.fn(async () => {}),
    handleRetry: vi.fn(async () => ({}) as never),
    ...overrides,
  } as ReturnType<typeof useSkillPage>
}

describe('SkillPage', () => {
  afterEach(cleanup)

  it('starts an eligible Skill without exposing diagnostic scores', () => {
    const handleStart = vi.fn(async () => {})
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'not-started',
          nextCompetencyId: null,
          nextActivityId: null,
          pendingAttemptId: null,
          pendingAttemptStatus: null,
          focusCompetencyId: null,
          competencies: [],
        },
        handleStart,
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(screen.getByText(/resultado consolidado ao final/i)).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar Habilidade' }))
    expect(handleStart).toHaveBeenCalledOnce()
  })

  it('explains a Curriculum coverage gap at start without entering diagnosis', () => {
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'not-started',
          nextCompetencyId: null,
          nextActivityId: null,
          pendingAttemptId: null,
          pendingAttemptStatus: null,
          focusCompetencyId: null,
          competencies: [],
        },
        startError:
          'O Currículo desta Habilidade ainda não tem cobertura suficiente para iniciar o diagnóstico.',
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(screen.getByRole('alert')).toHaveTextContent('cobertura suficiente')
    expect(
      screen.queryByRole('link', { name: 'Continuar diagnóstico' }),
    ).not.toBeInTheDocument()
  })

  it('resumes the next diagnostic Activity and shows no item result', () => {
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'diagnosing',
          nextCompetencyId: IDS.competencyId,
          nextActivityId: IDS.activityId,
          pendingAttemptId: null,
          pendingAttemptStatus: null,
          focusCompetencyId: null,
          competencies: [],
        },
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(screen.getByRole('link', { name: 'Continuar diagnóstico' })).toHaveAttribute(
      'data-params',
      expect.stringContaining(IDS.activityId),
    )
    expect(
      screen.queryByText(/resposta correta|resposta incorreta|nota de/i),
    ).not.toBeInTheDocument()
  })

  it('offers a safe retry for a failed diagnostic evaluation without exposing its result', () => {
    const handleRetryDiagnostic = vi.fn(async () => {})
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'diagnosing',
          nextCompetencyId: IDS.competencyId,
          nextActivityId: IDS.activityId,
          pendingAttemptId: '01SHF000000000000000000005',
          pendingAttemptStatus: 'failed',
          focusCompetencyId: null,
          competencies: [],
        },
        handleRetryDiagnostic,
      }),
    )
    render(<SkillPage goalId={IDS.goalId} skillId={IDS.skillId} />)
    expect(screen.getByText(/resposta enviada foi preservada/i)).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar avaliação novamente' }))
    expect(handleRetryDiagnostic).toHaveBeenCalledOnce()
    expect(
      screen.queryByRole('link', { name: 'Continuar diagnóstico' }),
    ).not.toBeInTheDocument()
  })

  it('shows only a consolidated Competency summary after diagnosis', () => {
    useSkillPageMock.mockReturnValue(
      controller({
        diagnostic: {
          status: 'learning',
          nextCompetencyId: null,
          nextActivityId: null,
          pendingAttemptId: null,
          pendingAttemptStatus: null,
          focusCompetencyId: IDS.competencyId,
          competencies: [
            {
              competencyId: IDS.competencyId,
              competencyName: 'Sequências',
              progress: 72,
            },
          ],
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
