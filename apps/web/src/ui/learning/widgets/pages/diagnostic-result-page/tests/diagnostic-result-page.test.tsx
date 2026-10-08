import type { ComponentProps } from 'react'

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DiagnosticOverview } from '@/core/learning/goal-detail'
import type { SkillExperienceDetail } from '@/core/learning/skill-experience'

import { DiagnosticResultPage } from '..'
import { useDiagnosticResultPage } from '../use-diagnostic-result-page'

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
vi.mock('../use-diagnostic-result-page', () => ({
  useDiagnosticResultPage: vi.fn(),
}))

const useDiagnosticResultPageMock = vi.mocked(useDiagnosticResultPage)
const IDS = {
  goalId: '01SHF000000000000000000001',
  skillId: '01SHF000000000000000000002',
  focusCompetencyId: '01SHF000000000000000000003',
  blockedCompetencyId: '01SHF000000000000000000004',
  activityId: '01SHF000000000000000000005',
  materialId: '01SHF000000000000000000006',
}

const diagnostic: DiagnosticOverview = {
  status: 'learning',
  runState: 'settled',
  readyToComplete: false,
  nextCompetencyId: null,
  nextActivityId: null,
  pendingAttemptId: null,
  pendingAttemptStatus: null,
  focusCompetencyId: IDS.focusCompetencyId,
  competencies: [
    {
      competencyId: IDS.focusCompetencyId,
      competencyName: 'Sequências',
      position: 1,
      progress: 58,
      coverageComplete: false,
      status: 'developing',
      isFocus: true,
      contentReleased: true,
    },
    {
      competencyId: IDS.blockedCompetencyId,
      competencyName: 'Funções',
      position: 2,
      progress: null,
      coverageComplete: false,
      status: 'learning',
      isFocus: false,
      contentReleased: false,
    },
  ],
  initialRecommendation: {
    competencyId: IDS.focusCompetencyId,
    competencyName: 'Sequências',
    activityId: IDS.activityId,
    activityTitle: 'Prática do diagnóstico',
    difficulty: 'easy',
    type: 'new-activity',
    reason: 'Retome a base observada no diagnóstico.',
    targetConceptName: 'Laços iniciais',
    materialId: null,
    gap: null,
  },
  initialOverallResult: 58,
  overallCoverageComplete: false,
  directCompletion: false,
}

const experience: SkillExperienceDetail = {
  goalId: IDS.goalId,
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
  skillStatus: 'learning',
  overallResult: 58,
  overallCoverageComplete: false,
  focusCompetencyId: IDS.focusCompetencyId,
  focusCompetencyName: 'Sequências',
  competencies: [
    {
      competencyId: IDS.focusCompetencyId,
      competencyName: 'Sequências',
      position: 1,
      progress: 58,
      coverageComplete: false,
      status: 'developing',
      availability: 'available',
      isFocus: true,
    },
    {
      competencyId: IDS.blockedCompetencyId,
      competencyName: 'Funções',
      position: 2,
      progress: null,
      coverageComplete: false,
      status: 'learning',
      availability: 'unavailable',
      isFocus: false,
    },
  ],
  recommendation: {
    competencyId: IDS.focusCompetencyId,
    competencyName: 'Sequências',
    activityId: IDS.activityId,
    activityTitle: 'Pratique sequências',
    difficulty: 'easy',
    type: 'new-activity',
    reason: 'Recomendação mutável após novas atividades.',
    targetConceptName: 'Outro conceito',
    materialId: null,
    gap: null,
  },
  recommendationGap: null,
  evaluation: null,
}

const props = { goalId: IDS.goalId, skillId: IDS.skillId }

function controller(overrides: Partial<ReturnType<typeof useDiagnosticResultPage>> = {}) {
  return {
    diagnostic,
    experience,
    isLoading: false,
    isPrivateAbsence: false,
    isRecoverableError: false,
    handleRetry: vi.fn(async () => ({}) as never),
    ...overrides,
  } as ReturnType<typeof useDiagnosticResultPage>
}

describe('DiagnosticResultPage', () => {
  afterEach(cleanup)

  it('shows the immutable diagnostic snapshot without question-level feedback', () => {
    useDiagnosticResultPageMock.mockReturnValue(controller())

    render(<DiagnosticResultPage {...props} />)

    expect(screen.getByRole('heading', { name: 'Seu ponto de partida' })).toBeVisible()
    expect(screen.getAllByText('58%')).toHaveLength(2)
    expect(screen.getByRole('button', { name: /Funções/ })).toHaveTextContent(
      'Sem evidência',
    )
    expect(
      screen.getByRole('heading', { name: 'Ponto de partida por Competência (0–100)' }),
    ).toBeVisible()
    expect(screen.getByText(/Retome a base observada no diagnóstico/)).toBeVisible()
    expect(screen.getByText('Laços iniciais', { exact: false })).toBeVisible()
    expect(
      screen.getByText(
        /O status de aprendizagem indica a evidência observada.*A recomendação abaixo é uma Atividade disponível/,
      ),
    ).toBeVisible()
    expect(screen.queryByText(/Recomendação mutável/)).not.toBeInTheDocument()
    expect(screen.queryByText('Outro conceito', { exact: false })).not.toBeInTheDocument()
    expect(screen.getByRole('main')).toHaveClass('pb-24')
    const competencyLabel = screen.getByRole('heading', {
      name: 'Ponto de partida por Competência (0–100)',
    })
    expect(
      competencyLabel.parentElement?.querySelector('div.border-control-border'),
    ).toHaveClass('border-control-border', 'bg-card')
    expect(screen.getByRole('link', { name: 'Continuar praticando' })).toHaveAttribute(
      'data-params',
      expect.stringContaining(IDS.activityId),
    )
    const skillLink = screen.getByRole('link', { name: 'Ver Habilidade' })
    expect(skillLink).toHaveAttribute('href', '/learning/goals/$goalId/skills/$skillId')
    expect(JSON.parse(skillLink.dataset.params ?? '{}')).toEqual({
      goalId: IDS.goalId,
      skillId: IDS.skillId,
    })
    expect(screen.queryByRole('link', { name: 'Escolher outra' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Ver Habilidade' })).toHaveLength(1)
    expect(
      screen.queryByText(/resposta correta|gabarito|sua nota foi/i),
    ).not.toBeInTheDocument()
  })

  it('states direct completion without claiming diagnostic improvement', () => {
    useDiagnosticResultPageMock.mockReturnValue(
      controller({
        diagnostic: { ...diagnostic, directCompletion: true },
        experience: { ...experience, recommendation: null },
      }),
    )

    render(<DiagnosticResultPage {...props} />)

    expect(screen.getByText(/concluiu a Habilidade sem indicar evolução/i)).toBeVisible()
    expect(screen.getByRole('link', { name: 'Ver Habilidade' })).toBeVisible()
  })

  it('offers the recommended material beside the activity when available', () => {
    const initialRecommendation = diagnostic.initialRecommendation
    if (!initialRecommendation)
      throw new Error('Expected a diagnostic recommendation fixture')
    useDiagnosticResultPageMock.mockReturnValue(
      controller({
        diagnostic: {
          ...diagnostic,
          initialRecommendation: {
            ...initialRecommendation,
            materialId: IDS.materialId,
          },
        },
      }),
    )

    render(<DiagnosticResultPage {...props} />)

    const material = screen.getByRole('link', { name: 'Ler material de apoio' })
    expect(material).toHaveAttribute(
      'href',
      '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/materials/$materialId',
    )
    expect(material).toHaveAttribute(
      'data-params',
      expect.stringContaining(IDS.materialId),
    )
    expect(screen.getByRole('link', { name: 'Continuar praticando' })).toBeVisible()
  })

  it('explains the immutable content gap when no initial recommendation exists', () => {
    useDiagnosticResultPageMock.mockReturnValue(
      controller({
        diagnostic: {
          ...diagnostic,
          initialRecommendation: null,
          initialRecommendationGap: 'curriculum_or_assessment_unavailable',
        },
        experience: {
          ...experience,
          recommendation: null,
          recommendationGap: 'Gap mutável após novas atividades.',
        },
      }),
    )

    render(<DiagnosticResultPage {...props} />)

    expect(
      screen.getByRole('heading', { name: 'Próximo passo indisponível' }),
    ).toBeVisible()
    expect(
      screen.getByText(
        'Não foi possível recomendar uma atividade de aprendizagem com o conteúdo disponível neste momento.',
      ),
    ).toBeVisible()
    expect(screen.queryByText(/Gap mutável/)).not.toBeInTheDocument()
  })

  it('keeps a private absence and a recoverable request failure distinct', () => {
    useDiagnosticResultPageMock.mockReturnValue(
      controller({ isPrivateAbsence: true, diagnostic: null, experience: null }),
    )
    const { rerender } = render(<DiagnosticResultPage {...props} />)
    expect(
      screen.getByRole('heading', { name: 'Resultado não encontrado' }),
    ).toBeVisible()

    useDiagnosticResultPageMock.mockReturnValue(
      controller({
        isPrivateAbsence: false,
        isRecoverableError: true,
        diagnostic: null,
        experience: null,
      }),
    )
    rerender(<DiagnosticResultPage {...props} />)
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeEnabled()
  })
})
