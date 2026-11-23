import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { EvolutionOption } from '@/core/learning/learning-panorama'
import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'
import type { LineChartProps } from '@/ui/shared/widgets/components/line-chart'

import { SkillEvolutionCard } from '..'
import { useSkillEvolutionCard } from '../use-skill-evolution-card'

vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-skill-evolution-card', () => ({ useSkillEvolutionCard: vi.fn() }))
vi.mock('@/ui/shared/widgets/components/line-chart', () => ({
  LineChart: ({ data, tone, title, baselineLabel }: LineChartProps) => (
    <div
      data-baseline-label={baselineLabel}
      data-testid='line-chart'
      data-title={title}
      data-tone={tone}
    >
      {data
        .map((datum) => `${datum.label} ${datum.valueLabel} ${datum.note ?? ''}`)
        .join('|')}
    </div>
  ),
}))

const useSkillEvolutionCardMock = vi.mocked(useSkillEvolutionCard)
const handleSelectSkillExperienceMock = vi.fn()
const handleRetryMock = vi.fn()

const options: EvolutionOption[] = [
  {
    skillExperienceId: 'exp-python',
    goalTitle: 'Carreira em dados',
    skillName: 'Python para análise de dados',
    status: 'learning',
  },
  {
    skillExperienceId: 'exp-logic',
    goalTitle: 'Aprender a programar',
    skillName: 'Lógica de programação',
    status: 'completed',
  },
]

const evolutionData: ChartDatum[] = [
  {
    key: 'p0',
    label: '28 set',
    value: 42,
    valueLabel: '42% (ponto de partida)',
    note: 'Parcial',
  },
  { key: 'p1', label: '5 out', value: 55, valueLabel: '55%' },
]

function makeHookValue(
  overrides: Partial<ReturnType<typeof useSkillEvolutionCard>> = {},
): ReturnType<typeof useSkillEvolutionCard> {
  return {
    state: 'success',
    selectedSkillExperienceId: 'exp-python',
    selectOptions: [
      { value: 'exp-python', label: 'Python para análise de dados' },
      { value: 'exp-logic', label: 'Lógica de programação' },
    ],
    evolutionData,
    baselineLabel: 'Ponto de partida · 42%',
    description:
      'Resultado da Habilidade após cada avaliação, desde o diagnóstico · pontos vazados são estimativas parciais',
    isRetrying: false,
    handleSelectSkillExperience: handleSelectSkillExperienceMock,
    handleRetry: handleRetryMock,
    ...overrides,
  }
}

function renderCard() {
  render(<SkillEvolutionCard defaultSkillExperienceId='exp-python' options={options} />)
  return screen.getByRole('region', { name: 'Evolução de uma Habilidade' })
}

describe('SkillEvolutionCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSkillEvolutionCardMock.mockReturnValue(makeHookValue())
  })

  afterEach(() => {
    cleanup()
  })

  it('passes its props to the owning hook', () => {
    renderCard()

    expect(useSkillEvolutionCardMock).toHaveBeenCalledWith({
      options,
      defaultSkillExperienceId: 'exp-python',
    })
  })

  it('renders the title, the partial-estimate caption and the evolution chart', () => {
    const card = renderCard()

    expect(
      within(card).getByText(
        'Resultado da Habilidade após cada avaliação, desde o diagnóstico · pontos vazados são estimativas parciais',
      ),
    ).toBeVisible()
    const chart = within(card).getByTestId('line-chart')
    expect(chart).toHaveAttribute('data-tone', 'jade')
    expect(chart).toHaveAttribute('data-title', 'Evolução de uma Habilidade')
    expect(chart).toHaveAttribute('data-baseline-label', 'Ponto de partida · 42%')
    expect(chart).toHaveTextContent('28 set 42% (ponto de partida) Parcial|5 out 55%')
  })

  it('shows the selected Habilidade in the closed select', () => {
    const card = renderCard()

    expect(
      within(card).getByRole('combobox', { name: 'Habilidade exibida no gráfico' }),
    ).toHaveTextContent('Python para análise de dados')
  })

  it('delegates the choice of another Habilidade to its hook', async () => {
    const card = renderCard()
    const user = userEvent.setup()

    await user.click(
      within(card).getByRole('combobox', { name: 'Habilidade exibida no gráfico' }),
    )
    await user.click(await screen.findByRole('option', { name: 'Lógica de programação' }))

    // The select primitive also passes its change details as a second argument.
    expect(handleSelectSkillExperienceMock).toHaveBeenCalledTimes(1)
    expect(handleSelectSkillExperienceMock.mock.calls[0][0]).toBe('exp-logic')
  })

  it('switches to a table that labels partial points as Parcial', async () => {
    const card = renderCard()

    await userEvent.setup().click(within(card).getByRole('tab', { name: 'Tabela' }))

    const table = await within(card).findByRole('table', {
      name: 'Evolução de uma Habilidade',
    })
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((header) => header.textContent),
    ).toEqual(['Data', 'Resultado', 'Estimativa'])
    expect(
      within(table)
        .getAllByRole('row')
        .slice(1)
        .map((row) => row.textContent),
    ).toEqual(['28 set42% (ponto de partida)Parcial', '5 out55%—'])
  })

  it('shows a busy placeholder while the selected series loads and keeps the select', () => {
    useSkillEvolutionCardMock.mockReturnValue(
      makeHookValue({ state: 'loading', evolutionData: [] }),
    )

    const card = renderCard()

    expect(
      within(card).getByRole('status', { name: 'Carregando a evolução da Habilidade' }),
    ).toHaveAttribute('aria-busy', 'true')
    expect(within(card).getByRole('combobox')).toBeVisible()
    expect(within(card).queryByTestId('line-chart')).not.toBeInTheDocument()
  })

  it('shows its own unavailable state with a working retry and keeps the select usable', () => {
    useSkillEvolutionCardMock.mockReturnValue(
      makeHookValue({ state: 'error', evolutionData: [] }),
    )

    const card = renderCard()

    expect(within(card).getByRole('alert')).toHaveTextContent(
      'Não foi possível carregar a evolução desta Habilidade.',
    )
    expect(within(card).getByRole('combobox')).toBeEnabled()

    fireEvent.click(within(card).getByRole('button', { name: 'Tentar novamente' }))

    expect(handleRetryMock).toHaveBeenCalledTimes(1)
    expect(within(card).queryByTestId('line-chart')).not.toBeInTheDocument()
  })

  it('disables the retry button while a retry is in flight', () => {
    useSkillEvolutionCardMock.mockReturnValue(
      makeHookValue({ state: 'error', isRetrying: true, evolutionData: [] }),
    )

    const card = renderCard()

    expect(within(card).getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })

  it('explains that the evolution appears after the first evaluations instead of empty axes', () => {
    useSkillEvolutionCardMock.mockReturnValue(
      makeHookValue({ state: 'empty', evolutionData: [], baselineLabel: undefined }),
    )

    const card = renderCard()

    expect(
      within(card).getByText(/aparecerão depois das primeiras avaliações/),
    ).toBeVisible()
    expect(within(card).queryByTestId('line-chart')).not.toBeInTheDocument()
    expect(within(card).queryByRole('tab', { name: 'Tabela' })).not.toBeInTheDocument()
    expect(
      within(card).queryByRole('button', { name: 'Tentar novamente' }),
    ).not.toBeInTheDocument()
  })

  it('hides the select when the account has no started experience', () => {
    useSkillEvolutionCardMock.mockReturnValue(
      makeHookValue({
        state: 'empty',
        selectOptions: [],
        selectedSkillExperienceId: null,
        evolutionData: [],
      }),
    )

    const card = renderCard()

    expect(within(card).queryByRole('combobox')).not.toBeInTheDocument()
    expect(
      within(card).getByText(/aparecerão depois das primeiras avaliações/),
    ).toBeVisible()
  })
})
