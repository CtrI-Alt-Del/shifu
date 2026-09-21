import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { SquareBackground } from '..'
import { useSquareBackground } from '../use-square-background'

vi.mock('../use-square-background', () => ({
  useSquareBackground: vi.fn(),
}))

const useSquareBackgroundMock = vi.mocked(useSquareBackground)

describe('SquareBackground', () => {
  it('renders an aria-hidden shared grid with the hook-provided cell count', () => {
    useSquareBackgroundMock.mockReturnValue({
      backgroundRef: { current: null },
      squareCount: 3,
    })

    render(<SquareBackground />)

    expect(document.querySelector('.square-background')).toHaveAttribute(
      'aria-hidden',
      'true',
    )
    expect(document.querySelectorAll('[data-square-background-cell]')).toHaveLength(3)
  })
})
