import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useSquareBackground } from '../use-square-background'

describe('useSquareBackground', () => {
  it('exposes the shared background ref and stable grid size', () => {
    const { result } = renderHook(() => useSquareBackground())

    expect(result.current.squareCount).toBe(700)
    expect(result.current.backgroundRef.current).toBeNull()
  })
})
