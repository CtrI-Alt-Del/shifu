import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { useReducedMotion } from 'motion/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AnimatedNumber } from '..'

vi.mock('motion/react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('motion/react')>()),
  useReducedMotion: vi.fn(() => false),
}))

const formatXp = (value: number) => `${new Intl.NumberFormat('pt-BR').format(value)} XP`

describe('AnimatedNumber', () => {
  afterEach(cleanup)

  it('counts up from zero to the formatted final value', async () => {
    render(<AnimatedNumber duration={0.3} format={formatXp} value={1240} />)

    expect(screen.getByText('0 XP')).toBeVisible()
    await waitFor(() => expect(screen.getByText('1.240 XP')).toBeVisible(), {
      timeout: 2000,
    })
  })

  it('shows the final value at once when motion is reduced', () => {
    vi.mocked(useReducedMotion).mockReturnValueOnce(true)
    render(<AnimatedNumber format={formatXp} value={1240} />)

    expect(screen.getByText('1.240 XP')).toBeVisible()
  })
})
