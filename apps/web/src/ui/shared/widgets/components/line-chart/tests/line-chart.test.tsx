import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'
import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'

import { LineChart } from '..'

vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))

const useReducedMotionPreferenceMock = vi.mocked(useReducedMotionPreference)

const TITLE = 'Evolução de uma Habilidade'
const DATA: ChartDatum[] = [
  { key: 'e1', label: '28 set', value: 42, valueLabel: '42%', note: 'Parcial' },
  { key: 'e2', label: '5 out', value: 55, valueLabel: '55%' },
  { key: 'e3', label: '19 out', value: 61, valueLabel: '61%', note: 'Parcial' },
  { key: 'e4', label: '16 nov', value: 68, valueLabel: '68%' },
]

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

function buildRect(width: number, height: number): DOMRect {
  return {
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: width,
    bottom: height,
    width,
    height,
    toJSON: () => ({}),
  }
}

// Recharts measures its container and its tick labels; jsdom has no layout, so
// the container gets a real size and every other element a small text size.
function stubContainerSize() {
  vi.stubGlobal('ResizeObserver', ResizeObserverStub)
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (
    this: Element,
  ) {
    return this.classList.contains('recharts-responsive-container')
      ? buildRect(600, 200)
      : buildRect(32, 14)
  })
}

describe('LineChart', () => {
  let warnSpy: ReturnType<typeof vi.spyOn>
  let errorSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    stubContainerSize()
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    useReducedMotionPreferenceMock.mockReturnValue({ prefersReducedMotion: true })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders one focusable application surface named by its title', () => {
    render(<LineChart data={DATA} title={TITLE} tone='jade' />)

    expect(screen.getByRole('application', { name: TITLE })).toHaveAttribute(
      'tabindex',
      '0',
    )
    expect(screen.getAllByRole('application')).toHaveLength(1)
    expect(warnSpy).not.toHaveBeenCalled()
    expect(errorSpy).not.toHaveBeenCalled()
  })

  it('draws the line and its wash from the jade token', () => {
    const { container } = render(<LineChart data={DATA} title={TITLE} tone='jade' />)

    expect(container.querySelector('.recharts-line-curve')).toHaveAttribute(
      'stroke',
      'var(--jade-text)',
    )
    expect(container.querySelector('.recharts-area-area')).toHaveAttribute(
      'fill',
      'var(--jade-text)',
    )
  })

  it('draws partial points hollow and the latest point as a filled marker', () => {
    const { container } = render(<LineChart data={DATA} title={TITLE} tone='jade' />)

    const dots = Array.from(container.querySelectorAll('.recharts-line-dots circle'))

    expect(dots.map((dot) => dot.getAttribute('fill'))).toEqual([
      'var(--card)',
      'var(--card)',
      'var(--jade-text)',
    ])
    expect(dots[0]).toHaveAttribute('stroke', 'var(--jade-text)')
    expect(dots[2]).toHaveAttribute('stroke', 'var(--card)')
  })

  it('hollows a partial latest point instead of filling it', () => {
    const partialLast: ChartDatum[] = [
      { key: 'e1', label: '28 set', value: 42, valueLabel: '42%' },
      { key: 'e2', label: '16 nov', value: 68, valueLabel: '68%', note: 'Parcial' },
    ]
    const { container } = render(
      <LineChart data={partialLast} title={TITLE} tone='jade' />,
    )

    const dots = Array.from(container.querySelectorAll('.recharts-line-dots circle'))

    expect(dots.map((dot) => dot.getAttribute('fill'))).toEqual(['var(--card)'])
  })

  it('labels only the latest value on the chart', () => {
    const { container } = render(<LineChart data={DATA} title={TITLE} tone='jade' />)

    const labels = container.querySelectorAll('.recharts-label-list text')

    expect(labels).toHaveLength(1)
    expect(labels[0]).toHaveTextContent('68%')
  })

  it('draws the base line at the starting point with its label', () => {
    const { container } = render(
      <LineChart
        baselineLabel='Ponto de partida · 42%'
        data={DATA}
        title={TITLE}
        tone='jade'
      />,
    )

    expect(container.querySelectorAll('.recharts-reference-line')).toHaveLength(1)
    expect(screen.getByText('Ponto de partida · 42%')).toBeInTheDocument()
    expect(warnSpy).not.toHaveBeenCalled()
  })

  it('draws no base line without a baseline label', () => {
    const { container } = render(<LineChart data={DATA} title={TITLE} tone='jade' />)

    expect(container.querySelector('.recharts-reference-line')).toBeNull()
  })

  it('shows the percentage scale and takes axis text and gridlines from tokens', () => {
    const { container } = render(<LineChart data={DATA} title={TITLE} tone='jade' />)

    const yTicks = Array.from(
      container.querySelectorAll('.recharts-yAxis-tick-labels text'),
    )

    expect(yTicks.map((tick) => tick.textContent)).toEqual(['0%', '50%', '100%'])
    expect(yTicks[0]).toHaveAttribute('fill', 'var(--muted-foreground)')
    expect(
      container.querySelector('.recharts-cartesian-grid-horizontal line'),
    ).toHaveAttribute('stroke', 'var(--border)')
  })

  it('announces the label, value and Parcial note of the point the arrow keys reach', () => {
    render(<LineChart data={DATA} title={TITLE} tone='jade' />)
    const surface = screen.getByRole('application', { name: TITLE })

    act(() => surface.focus())

    const status = screen.getByRole('status')

    expect(status).toHaveAttribute('aria-live', 'assertive')
    expect(status).toHaveTextContent('28 set42%Parcial')

    fireEvent.keyDown(surface, { key: 'ArrowRight' })

    expect(status).toHaveTextContent('5 out55%')
    expect(status).not.toHaveTextContent('Parcial')

    fireEvent.keyDown(surface, { key: 'ArrowRight' })

    expect(status).toHaveTextContent('19 out61%Parcial')

    fireEvent.keyDown(surface, { key: 'ArrowLeft' })

    expect(status).toHaveTextContent('5 out55%')
  })

  it('renders without warnings when animations are enabled', () => {
    useReducedMotionPreferenceMock.mockReturnValue({ prefersReducedMotion: false })
    const { container } = render(<LineChart data={DATA} title={TITLE} tone='jade' />)

    expect(container.querySelector('.recharts-line-curve')).toBeInTheDocument()
    expect(warnSpy).not.toHaveBeenCalled()
    expect(errorSpy).not.toHaveBeenCalled()
  })

  it('renders an empty series without warnings', () => {
    render(
      <LineChart baselineLabel='Ponto de partida' data={[]} title={TITLE} tone='jade' />,
    )

    expect(screen.getByRole('application', { name: TITLE })).toBeInTheDocument()
    expect(warnSpy).not.toHaveBeenCalled()
    expect(errorSpy).not.toHaveBeenCalled()
  })

  it('renders a single point without warnings', () => {
    const { container } = render(
      <LineChart data={DATA.slice(0, 1)} title={TITLE} tone='jade' />,
    )

    expect(container.querySelectorAll('.recharts-line-dots circle')).toHaveLength(1)
    expect(warnSpy).not.toHaveBeenCalled()
    expect(errorSpy).not.toHaveBeenCalled()
  })
})
