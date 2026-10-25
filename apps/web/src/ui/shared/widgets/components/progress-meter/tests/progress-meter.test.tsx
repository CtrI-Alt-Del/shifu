import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProgressMeter } from '..'

vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))

describe('ProgressMeter', () => {
  afterEach(cleanup)

  it('preserves the primary tone and bounded accessible value by default', () => {
    render(<ProgressMeter label='Progresso' value={120} />)

    expect(screen.getByRole('progressbar', { name: 'Progresso' })).toHaveAttribute(
      'aria-valuenow',
      '100',
    )
    expect(screen.getByText('100%')).toHaveClass('text-primary')
  })

  it('renders the success tone without changing progress semantics', () => {
    render(<ProgressMeter label='Progresso da Competência' tone='success' value={72} />)

    expect(
      screen.getByRole('progressbar', { name: 'Progresso da Competência' }),
    ).toHaveAttribute('aria-valuenow', '72')
    expect(screen.getByText('72%')).toHaveClass('text-success')
  })

  it('shows the final figure and fill width at once under reduced motion', () => {
    render(<ProgressMeter label='Progresso da Competência' value={64.4} />)

    const meter = screen.getByRole('progressbar', { name: 'Progresso da Competência' })
    expect(screen.getByText('64%')).toBeVisible()
    expect(meter).toHaveAttribute('aria-valuetext', '64%')
    expect((meter.firstElementChild as HTMLElement).style.width).toBe('64.4%')
  })
})
