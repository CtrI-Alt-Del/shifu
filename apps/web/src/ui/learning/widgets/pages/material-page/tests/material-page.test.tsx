import type { ComponentProps } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  AvailableMaterialDetail,
  UnavailableMaterialDetail,
} from '@/core/learning/material-detail'

import { MaterialPage } from '..'
import { type MaterialPageController, useMaterialPage } from '../use-material-page'

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

vi.mock('../use-material-page', () => ({
  useMaterialPage: vi.fn(),
}))

const useMaterialPageMock = vi.mocked(useMaterialPage)

const IDS = {
  activityId: '01SHF000000000000000000005',
  competencyId: '01SHF000000000000000000001',
  focusCompetencyId: '01SHF000000000000000000002',
  goalId: '01SHF000000000000000000003',
  materialId: '01SHF000000000000000000006',
  skillId: '01SHF000000000000000000004',
}

const pageProps = {
  competencyId: IDS.competencyId,
  goalId: IDS.goalId,
  materialId: IDS.materialId,
  skillId: IDS.skillId,
}

const availableDetail: AvailableMaterialDetail = {
  availability: 'available',
  competencyId: IDS.competencyId,
  competencyName: 'Estruturas de repetição',
  content: 'O laço percorre uma sequência.\n\n```python\nprint(1)\n```',
  goalId: IDS.goalId,
  materialId: IDS.materialId,
  materialTitle: 'Repetição com for',
  recommendation: {
    activityId: IDS.activityId,
    competencyId: IDS.competencyId,
    difficulty: 'hard',
    type: 'new-activity',
  },
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
}

const unavailableDetail: UnavailableMaterialDetail = {
  availability: 'unavailable',
  competencyId: IDS.competencyId,
  competencyName: 'Funções',
  focusCompetencyId: IDS.focusCompetencyId,
  focusCompetencyName: 'Fundamentos de lógica',
  goalId: IDS.goalId,
  materialId: IDS.materialId,
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
}

function controller(
  overrides: Partial<MaterialPageController> = {},
): MaterialPageController {
  return {
    detail: availableDetail,
    error: null,
    handleOpenRecommendation: vi.fn(),
    handleRetry: vi.fn(),
    hasActivityFailure: false,
    isLoading: false,
    isOpeningActivity: false,
    isPrivateAbsence: false,
    isRecoverableError: false,
    ...overrides,
  }
}

describe('MaterialPage', () => {
  beforeEach(() => {
    useMaterialPageMock.mockReturnValue(controller())
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('announces the loading state while the material is unresolved', () => {
    useMaterialPageMock.mockReturnValue(controller({ detail: null, isLoading: true }))

    render(<MaterialPage {...pageProps} />)

    expect(
      screen.getByRole('status', { name: 'Carregando Material de apoio...' }),
    ).toBeVisible()
  })

  it('keeps a private absence generic instead of naming the material', () => {
    useMaterialPageMock.mockReturnValue(
      controller({ detail: null, isPrivateAbsence: true }),
    )

    render(<MaterialPage {...pageProps} />)

    expect(
      screen.getByRole('heading', { level: 1, name: 'Recurso não encontrado' }),
    ).toBeVisible()
    expect(screen.queryByText('Repetição com for')).not.toBeInTheDocument()
  })

  it('offers a retry action when loading the material failed', () => {
    const handleRetry = vi.fn()
    useMaterialPageMock.mockReturnValue(
      controller({ detail: null, handleRetry, isRecoverableError: true }),
    )

    render(<MaterialPage {...pageProps} />)
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Não foi possível carregar este Material',
      }),
    ).toBeVisible()
    expect(handleRetry).toHaveBeenCalledTimes(1)
  })

  it('hides the content and names the focus when the Competency is not released', () => {
    useMaterialPageMock.mockReturnValue(controller({ detail: unavailableDetail }))

    render(<MaterialPage {...pageProps} />)

    expect(
      screen.getByRole('heading', { level: 1, name: 'Material ainda indisponível' }),
    ).toBeVisible()
    expect(screen.getByText(/Fundamentos de lógica/)).toBeVisible()
    expect(screen.queryByText('O laço percorre uma sequência.')).not.toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Voltar para a Competência' }),
    ).toHaveAttribute(
      'data-to',
      '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId',
    )
  })

  it('does not ask the reader to advance in the blocked Competency itself', () => {
    useMaterialPageMock.mockReturnValue(
      controller({
        detail: {
          ...unavailableDetail,
          focusCompetencyId: unavailableDetail.competencyId,
          focusCompetencyName: unavailableDetail.competencyName,
        },
      }),
    )

    render(<MaterialPage {...pageProps} />)

    expect(
      screen.getByText(
        'O conteúdo da Competência Funções ainda não foi liberado nesta Habilidade.',
      ),
    ).toBeVisible()
    expect(screen.queryByText(/Avance em Funções/)).not.toBeInTheDocument()
  })

  it('explains the blocked Competency without a known focus', () => {
    useMaterialPageMock.mockReturnValue(
      controller({
        detail: {
          ...unavailableDetail,
          focusCompetencyId: null,
          focusCompetencyName: null,
        },
      }),
    )

    render(<MaterialPage {...pageProps} />)

    expect(
      screen.getByText(
        'O conteúdo da Competência Funções ainda não foi liberado nesta Habilidade.',
      ),
    ).toBeVisible()
  })

  it('renders the official markdown of a released material', () => {
    render(<MaterialPage {...pageProps} />)

    expect(
      screen.getByRole('heading', { level: 1, name: 'Repetição com for' }),
    ).toBeVisible()
    expect(screen.getByText('O laço percorre uma sequência.')).toBeVisible()
    expect(
      screen.getByRole('region', { name: 'Bloco de código em python' }),
    ).toBeVisible()
  })

  it('returns to the Competency of origin with its explicit params', () => {
    render(<MaterialPage {...pageProps} />)

    const back = screen.getByRole('link', {
      name: 'Voltar para a Competência Estruturas de repetição',
    })

    expect(back).toHaveAttribute(
      'data-to',
      '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId',
    )
    expect(back).toHaveAttribute(
      'data-params',
      JSON.stringify({
        competencyId: IDS.competencyId,
        goalId: IDS.goalId,
        skillId: IDS.skillId,
      }),
    )
  })

  it('opens the recommendation of the source Competency when selected', () => {
    const handleOpenRecommendation = vi.fn()
    useMaterialPageMock.mockReturnValue(controller({ handleOpenRecommendation }))

    render(<MaterialPage {...pageProps} />)
    fireEvent.click(screen.getByRole('button', { name: 'Praticar' }))

    expect(handleOpenRecommendation).toHaveBeenCalledWith(IDS.activityId)
  })

  it('omits the whole recommendation block when none is available', () => {
    useMaterialPageMock.mockReturnValue(
      controller({ detail: { ...availableDetail, recommendation: null } }),
    )

    render(<MaterialPage {...pageProps} />)

    expect(screen.queryByRole('button', { name: 'Praticar' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Continuar em/)).not.toBeInTheDocument()
    expect(screen.getByText('O laço percorre uma sequência.')).toBeVisible()
  })

  it('disables the recommendation while the Activity is opening', () => {
    useMaterialPageMock.mockReturnValue(controller({ isOpeningActivity: true }))

    render(<MaterialPage {...pageProps} />)

    expect(screen.getByRole('button', { name: 'Abrindo...' })).toBeDisabled()
  })

  it('keeps the material visible and recoverable when the Activity fails to open', () => {
    useMaterialPageMock.mockReturnValue(controller({ hasActivityFailure: true }))

    render(<MaterialPage {...pageProps} />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível abrir a atividade recomendada.',
    )
    expect(screen.getByText('O laço percorre uma sequência.')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Tentar abrir novamente' })).toBeEnabled()
  })
})
