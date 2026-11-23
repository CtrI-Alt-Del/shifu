import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'
import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'

import { BarChart } from '..'

vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))

const useReducedMotionPreferenceMock = vi.mocked(useReducedMotionPreference)

const TITLE = 'Atividades avaliadas por semana'
const DATA: ChartDatum[] = [
  { key: 'w1', label: '28 set', value: 3, valueLabel: '3 atividades' },
  { key: 'w2', label: '5 out', value: 5, valueLabel: '5 atividades' },
  { key: 'w3', label: '12 out', value: 0, valueLabel: '0 atividades' },
  { key: 'w4', label: '19 out', value: 8, valueLabel: '8 atividades', note: 'Parcial' },
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

describe('BarChart', () => {
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
    render(<BarChart data={DATA} title={TITLE} tone='jade' />)

    const surface = screen.getByRole('application', { name: TITLE })

    expect(surface).toHaveAttribute('tabindex', '0')
    expect(screen.getAllByRole('application')).toHaveLength(1)
    expect(warnSpy).not.toHaveBeenCalled()
    expect(errorSpy).not.toHaveBeenCalled()
  })

  it('draws a bar per non-zero datum and an axis label for every week', () => {
    const { container } = render(<BarChart data={DATA} title={TITLE} tone='jade' />)

    expect(container.querySelectorAll('.recharts-bar-rectangle')).toHaveLength(3)
    for (const datum of DATA) {
      expect(screen.getAllByText(datum.label).length).toBeGreaterThan(0)
    }
    expect(warnSpy).not.toHaveBeenCalled()
  })

  it('colors the bars from the jade token', () => {
    const { container } = render(<BarChart data={DATA} title={TITLE} tone='jade' />)

    expect(container.querySelector('.recharts-bar-rectangle path')).toHaveAttribute(
      'fill',
      'var(--jade-solid)',
    )
  })

  it('colors the bars from the latão token', () => {
    const { container } = render(<BarChart data={DATA} title={TITLE} tone='latao' />)

    expect(container.querySelector('.recharts-bar-rectangle path')).toHaveAttribute(
      'fill',
      'var(--latao-fill)',
    )
  })

  it('takes axis text from the muted foreground and gridlines from the border token', () => {
    const { container } = render(<BarChart data={DATA} title={TITLE} tone='jade' />)

    expect(container.querySelector('.recharts-xAxis-tick-labels text')).toHaveAttribute(
      'fill',
      'var(--muted-foreground)',
    )
    expect(container.querySelector('.recharts-yAxis-tick-labels text')).toHaveAttribute(
      'fill',
      'var(--muted-foreground)',
    )
    expect(
      container.querySelector('.recharts-cartesian-grid-horizontal line'),
    ).toHaveAttribute('stroke', 'var(--border)')
  })

  it('labels the last bar with its value when highlightLast is set', () => {
    const { container } = render(
      <BarChart data={DATA} highlightLast title={TITLE} tone='latao' />,
    )

    const labels = container.querySelectorAll('.recharts-label-list text')

    expect(labels).toHaveLength(1)
    expect(labels[0]).toHaveTextContent('8 atividades')
  })

  it('does not label any bar by default', () => {
    const { container } = render(<BarChart data={DATA} title={TITLE} tone='jade' />)

    expect(container.querySelector('.recharts-label-list')).toBeNull()
  })

  it('announces only the label and value of the point the arrow keys reach', () => {
    render(<BarChart data={DATA} title={TITLE} tone='jade' />)
    const surface = screen.getByRole('application', { name: TITLE })

    act(() => surface.focus())

    const status = screen.getByRole('status')

    expect(status).toHaveAttribute('aria-live', 'assertive')
    expect(status).toHaveTextContent('28 set3 atividades')
    expect(status).not.toHaveTextContent('Parcial')

    fireEvent.keyDown(surface, { key: 'ArrowRight' })

    expect(status).toHaveTextContent('5 out5 atividades')

    fireEvent.keyDown(surface, { key: 'ArrowLeft' })

    expect(status).toHaveTextContent('28 set3 atividades')
  })

  it('shows the note of a point when it has one', () => {
    render(<BarChart data={DATA} title={TITLE} tone='jade' />)
    const surface = screen.getByRole('application', { name: TITLE })

    act(() => surface.focus())
    for (let step = 0; step < DATA.length - 1; step += 1) {
      fireEvent.keyDown(surface, { key: 'ArrowRight' })
    }

    expect(screen.getByRole('status')).toHaveTextContent('19 out8 atividadesParcial')
  })

  it('renders without warnings when animations are enabled', () => {
    useReducedMotionPreferenceMock.mockReturnValue({ prefersReducedMotion: false })
    const { container } = render(<BarChart data={DATA} title={TITLE} tone='jade' />)

    expect(container.querySelectorAll('.recharts-bar-rectangle').length).toBeGreaterThan(
      0,
    )
    expect(warnSpy).not.toHaveBeenCalled()
    expect(errorSpy).not.toHaveBeenCalled()
  })

  it('renders an empty series without warnings', () => {
    render(<BarChart data={[]} highlightLast title={TITLE} tone='jade' />)

    expect(screen.getByRole('application', { name: TITLE })).toBeInTheDocument()
    expect(warnSpy).not.toHaveBeenCalled()
    expect(errorSpy).not.toHaveBeenCalled()
  })
})
