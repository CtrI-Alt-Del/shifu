import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useChartFrame } from '../use-chart-frame'

describe('useChartFrame', () => {
  it('starts in the chart view with a stable heading id', () => {
    const { result, rerender } = renderHook(() => useChartFrame())
    const { headingId } = result.current

    expect(result.current.view).toBe('chart')
    expect(headingId).not.toBe('')

    rerender()

    expect(result.current.headingId).toBe(headingId)
  })

  it('switches to the table view and back to the chart', () => {
    const { result } = renderHook(() => useChartFrame())

    act(() => result.current.handleViewChange('table'))

    expect(result.current.view).toBe('table')

    act(() => result.current.handleViewChange('chart'))

    expect(result.current.view).toBe('chart')
  })

  it('ignores a value that is not a known view', () => {
    const { result } = renderHook(() => useChartFrame())

    act(() => result.current.handleViewChange('table'))
    act(() => result.current.handleViewChange('grid'))

    expect(result.current.view).toBe('table')
  })

  it('gives each frame its own heading id', () => {
    const first = renderHook(() => useChartFrame())
    const second = renderHook(() => useChartFrame())

    expect(first.result.current.headingId).not.toBe(second.result.current.headingId)
  })
})
