import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ProgressMeter } from '..'

describe('ProgressMeter', () => {
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
})
