import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { type ChartDatum, ChartFrame, type ChartFrameProps } from '..'
import { useChartFrame } from '../use-chart-frame'

vi.mock('../use-chart-frame', () => ({ useChartFrame: vi.fn() }))

const useChartFrameMock = vi.mocked(useChartFrame)
const handleViewChangeMock = vi.fn()

const ROWS: ChartDatum[] = [
  { key: 'w1', label: '9 nov', value: 5, valueLabel: '5 atividades' },
  { key: 'w2', label: '16 nov', value: 8, valueLabel: '8 atividades', note: 'Parcial' },
]

function buildProps(overrides: Partial<ChartFrameProps> = {}): ChartFrameProps {
  return {
    title: 'Atividades avaliadas por semana',
    description: 'Últimas 8 semanas, em todas as suas Habilidades',
    columns: ['Semana', 'Atividades', 'Observação'],
    rows: ROWS,
    children: <div data-testid='chart-surface' />,
    ...overrides,
  }
}

function mockView(view: 'chart' | 'table') {
  useChartFrameMock.mockReturnValue({
    headingId: 'chart-frame-heading',
    view,
    handleViewChange: handleViewChangeMock,
  })
}

describe('ChartFrame', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockView('chart')
  })
  afterEach(cleanup)

  it('names the card by its title and shows the text summary and the chart', () => {
    render(<ChartFrame {...buildProps()} />)

    const card = screen.getByRole('region', { name: 'Atividades avaliadas por semana' })

    expect(
      within(card).getByRole('heading', { name: 'Atividades avaliadas por semana' }),
    ).toBeVisible()
    expect(
      within(card).getByText('Últimas 8 semanas, em todas as suas Habilidades'),
    ).toBeVisible()
    expect(screen.getByTestId('chart-surface')).toBeVisible()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('renders the Gráfico and Tabela switch with the chart view selected', () => {
    render(<ChartFrame {...buildProps()} />)

    const switchList = screen.getByRole('tablist', {
      name: 'Visualização de Atividades avaliadas por semana',
    })

    expect(within(switchList).getByRole('tab', { name: 'Gráfico' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(within(switchList).getByRole('tab', { name: 'Tabela' })).toHaveAttribute(
      'aria-selected',
      'false',
    )
  })

  it('keeps both switch segments at the 44 px touch target', () => {
    render(<ChartFrame {...buildProps()} />)

    expect(screen.getByRole('tab', { name: 'Gráfico' })).toHaveClass('min-h-11!')
    expect(screen.getByRole('tab', { name: 'Tabela' })).toHaveClass('min-h-11!')
  })

  it('delegates the view change to its hook when Tabela is chosen', async () => {
    const user = userEvent.setup()
    render(<ChartFrame {...buildProps()} />)

    await user.click(screen.getByRole('tab', { name: 'Tabela' }))

    expect(handleViewChangeMock).toHaveBeenCalledWith('table')
  })

  it('replaces the chart with a captioned table of the same values', () => {
    mockView('table')
    render(<ChartFrame {...buildProps()} />)

    const table = screen.getByRole('table', { name: 'Atividades avaliadas por semana' })
    const headers = within(table).getAllByRole('columnheader')
    const bodyRows = within(table).getAllByRole('row').slice(1)

    expect(table.querySelector('caption')).toHaveTextContent(
      'Atividades avaliadas por semana',
    )
    expect(headers.map((header) => header.textContent)).toEqual([
      'Semana',
      'Atividades',
      'Observação',
    ])
    expect(bodyRows.map((row) => row.textContent)).toEqual([
      '9 nov5 atividades—',
      '16 nov8 atividadesParcial',
    ])
    expect(screen.queryByTestId('chart-surface')).not.toBeInTheDocument()
  })

  it('omits the note column when the table has two columns', () => {
    mockView('table')
    render(<ChartFrame {...buildProps({ columns: ['Semana', 'Atividades'] })} />)

    const table = screen.getByRole('table')

    expect(within(table).getAllByRole('columnheader')).toHaveLength(2)
    expect(within(table).getAllByRole('row')[2]).toHaveTextContent('16 nov8 atividades')
    expect(within(table).queryByText('Parcial')).not.toBeInTheDocument()
  })

  it('renders the action beside the summary', () => {
    render(
      <ChartFrame {...buildProps({ action: <a href='/xp'>Ver histórico de XP</a> })} />,
    )

    expect(screen.getByRole('link', { name: 'Ver histórico de XP' })).toBeVisible()
  })

  it('renders the header action in the header beside the switch', () => {
    render(
      <ChartFrame
        {...buildProps({ headerAction: <a href='/xp'>Ver histórico de XP</a> })}
      />,
    )

    const link = screen.getByRole('link', { name: 'Ver histórico de XP' })
    // The link shares the title row; on a narrow screen the switch drops below
    // both, and from `sm` on title, link and switch share one row.
    expect(
      within(link.parentElement as HTMLElement).getByRole('heading', {
        name: 'Atividades avaliadas por semana',
      }),
    ).toBeVisible()
    expect(screen.getByRole('tablist')).toBeVisible()
  })

  it('keeps the footnote visible in both the chart and the table view', () => {
    const { rerender } = render(
      <ChartFrame {...buildProps({ footnote: 'O valor é uma contagem.' })} />,
    )
    expect(screen.getByTestId('chart-surface')).toBeInTheDocument()
    expect(screen.getByText('O valor é uma contagem.')).toBeVisible()

    mockView('table')
    rerender(<ChartFrame {...buildProps({ footnote: 'O valor é uma contagem.' })} />)
    expect(screen.getByRole('table')).toBeVisible()
    expect(screen.getByText('O valor é uma contagem.')).toBeVisible()
  })

  it('omits the footnote in the empty state, where there is no chart to qualify', () => {
    render(
      <ChartFrame
        {...buildProps({
          emptyMessage: 'Sem avaliações ainda.',
          footnote: 'O valor é uma contagem.',
        })}
      />,
    )

    expect(screen.queryByText('O valor é uma contagem.')).not.toBeInTheDocument()
  })

  it('shows the empty message instead of the switch and the chart', () => {
    render(
      <ChartFrame
        {...buildProps({
          emptyMessage: 'Os gráficos aparecem depois das primeiras avaliações.',
        })}
      />,
    )

    expect(
      screen.getByText('Os gráficos aparecem depois das primeiras avaliações.'),
    ).toBeVisible()
    expect(
      screen.getByText('Últimas 8 semanas, em todas as suas Habilidades'),
    ).toBeVisible()
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
    expect(screen.queryByTestId('chart-surface')).not.toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('keeps the action visible in the empty state', () => {
    render(
      <ChartFrame
        {...buildProps({
          emptyMessage: 'Sem avaliações ainda.',
          action: <a href='/xp'>Ver histórico de XP</a>,
        })}
      />,
    )

    expect(screen.getByRole('link', { name: 'Ver histórico de XP' })).toBeVisible()
  })
})
