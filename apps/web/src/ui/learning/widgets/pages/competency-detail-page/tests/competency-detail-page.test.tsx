import type { ComponentProps } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  AvailableCompetencyDetail,
  UnavailableCompetencyDetail,
} from '@/core/learning/competency-detail'

import { CompetencyDetailPage } from '..'
import {
  type CompetencyDetailPageController,
  useCompetencyDetailPage,
} from '../use-competency-detail-page'

type LinkMockProps = Omit<ComponentProps<'a'>, 'href'> & {
  params?: Record<string, string>
  to: string
}

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, params, to, ...props }: LinkMockProps) => (
    <a data-params={JSON.stringify(params)} data-to={to} href={to} {...props}>
      {children}
    </a>
  ),
}))

vi.mock('../use-competency-detail-page', () => ({
  useCompetencyDetailPage: vi.fn(),
}))

const useCompetencyDetailPageMock = vi.mocked(useCompetencyDetailPage)

const IDS = {
  activityId: '01SHF000000000000000000005',
  competencyId: '01SHF000000000000000000001',
  focusCompetencyId: '01SHF000000000000000000002',
  goalId: '01SHF000000000000000000003',
  materialId: '01SHF000000000000000000006',
  skillId: '01SHF000000000000000000004',
}

const availableDetail: AvailableCompetencyDetail = {
  availability: 'available',
  competencyId: IDS.competencyId,
  competencyName: 'Estruturas de repetição',
  focusCompetencyId: IDS.focusCompetencyId,
  focusCompetencyName: 'Fundamentos de lógica',
  focusReturned: false,
  goalId: IDS.goalId,
  isFocus: true,
  items: [
    {
      id: IDS.materialId,
      kind: 'material',
      position: 1,
      title: 'Repetição com for',
    },
    {
      activityType: 'learning',
      difficulty: 'hard',
      id: IDS.activityId,
      kind: 'activity',
      latestScore: null,
      position: 2,
      title: 'Somar os números pares de uma lista',
    },
  ],
  progress: 72,
  recommendation: {
    activityId: IDS.activityId,
    competencyId: IDS.competencyId,
    difficulty: 'hard',
    type: 'new-activity',
  },
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
  status: 'proficient',
}

const unavailableDetail: UnavailableCompetencyDetail = {
  availability: 'unavailable',
  competencyId: IDS.competencyId,
  competencyName: 'Estruturas de repetição',
  focusCompetencyId: IDS.focusCompetencyId,
  focusCompetencyName: 'Fundamentos de lógica',
  goalId: IDS.goalId,
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
}

function makeController(
  overrides: Partial<CompetencyDetailPageController> = {},
): CompetencyDetailPageController {
  return {
    detail: null,
    error: null,
    handleRetry: vi.fn(() => Promise.resolve({} as never)),
    isLoading: false,
    isPrivateAbsence: false,
    isRecoverableError: false,
    ...overrides,
  }
}

describe('CompetencyDetailPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    useCompetencyDetailPageMock.mockReturnValue(makeController())
  })

  it('renders loading, private absence and recoverable error states without stale detail', () => {
    useCompetencyDetailPageMock.mockReturnValue(makeController({ isLoading: true }))
    const { rerender } = render(
      <CompetencyDetailPage
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Carregando Competência')

    useCompetencyDetailPageMock.mockReturnValue(
      makeController({ isPrivateAbsence: true }),
    )
    rerender(
      <CompetencyDetailPage
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )
    expect(screen.getByRole('heading', { name: 'Recurso não encontrado' })).toBeVisible()

    useCompetencyDetailPageMock.mockReturnValue(
      makeController({ isRecoverableError: true }),
    )
    rerender(
      <CompetencyDetailPage
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )
    expect(
      screen.getByRole('heading', { name: 'Não foi possível carregar esta Competência' }),
    ).toBeVisible()
  })

  it('renders available content, focus state and recommendation through real child widgets', () => {
    useCompetencyDetailPageMock.mockReturnValue(
      makeController({ detail: availableDetail }),
    )
    render(
      <CompetencyDetailPage
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Estruturas de repetição' })).toBeVisible()
    expect(screen.getByRole('list', { name: 'Conteúdos da Competência' })).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Praticar Somar os números pares de uma lista' }),
    ).toBeVisible()
    expect(screen.getByText('Difícil · Recomendada')).toBeVisible()
  })

  it('explains the Concept target and offers optional Material alongside direct practice', () => {
    useCompetencyDetailPageMock.mockReturnValue(
      makeController({
        detail: {
          ...availableDetail,
          adaptive: {
            targetConceptId: IDS.competencyId,
            originalTargetConceptId: IDS.competencyId,
            targetConceptName: 'Laços de repetição',
            reason: 'coverage',
            difficulty: 'easy',
            activityId: IDS.activityId,
            materialId: IDS.materialId,
            materialIsOptional: true,
            gap: null,
          },
          coverageComplete: false,
        },
      }),
    )
    render(
      <CompetencyDetailPage
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Laços de repetição' })).toBeVisible()
    expect(screen.getByText(/cobertura de evidências.*incompleta/i)).toBeVisible()
    expect(screen.getByRole('link', { name: 'Ler Material opcional' })).toBeVisible()
    expect(
      screen.getByRole('link', { name: /Somar os números pares.*Fácil/ }),
    ).toBeVisible()
    expect(
      screen.getByText('O Material é opcional. Você pode começar pela Atividade.'),
    ).toBeVisible()
  })

  it('keeps official progress unknown while v2 Concept coverage is incomplete', () => {
    useCompetencyDetailPageMock.mockReturnValue(
      makeController({
        detail: {
          ...availableDetail,
          progress: null,
          coverageComplete: false,
          adaptive: {
            targetConceptId: IDS.competencyId,
            originalTargetConceptId: IDS.competencyId,
            targetConceptName: 'Laços de repetição',
            reason: 'coverage',
            difficulty: 'easy',
            activityId: IDS.activityId,
            materialId: IDS.materialId,
            materialIsOptional: true,
            gap: null,
          },
        },
      }),
    )
    render(
      <CompetencyDetailPage
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )

    expect(
      screen.getByText('Progresso da Competência: ainda sem evidência suficiente.'),
    ).toBeVisible()
    expect(
      screen.queryByRole('progressbar', { name: 'Progresso da Competência' }),
    ).not.toBeInTheDocument()
    expect(screen.getByText(/cobertura de evidências.*incompleta/i)).toBeVisible()
  })

  it('renders unavailable content without progress or released sequence', () => {
    useCompetencyDetailPageMock.mockReturnValue(
      makeController({ detail: unavailableDetail }),
    )
    render(
      <CompetencyDetailPage
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )

    expect(
      screen.getByRole('heading', { name: 'Competência ainda indisponível' }),
    ).toBeVisible()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
    expect(
      screen.queryByText('Somar os números pares de uma lista'),
    ).not.toBeInTheDocument()
  })

  it('exposes one explicit retry action', () => {
    const retryMock = vi.fn(() => Promise.resolve({} as never))
    useCompetencyDetailPageMock.mockReturnValue(
      makeController({ isRecoverableError: true, handleRetry: retryMock }),
    )
    render(
      <CompetencyDetailPage
        competencyId={IDS.competencyId}
        goalId={IDS.goalId}
        skillId={IDS.skillId}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(retryMock).toHaveBeenCalledOnce()
  })
})
