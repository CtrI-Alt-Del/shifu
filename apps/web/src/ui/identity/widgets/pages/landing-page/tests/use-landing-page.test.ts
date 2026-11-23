import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useLandingPage } from '../use-landing-page'

describe('useLandingPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('keeps motion paused until the visible document is hydrated', () => {
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')

    const { result } = renderHook(useLandingPage)

    expect(result.current.isDocumentVisible).toBe(false)
  })

  it('pauses and resumes decorative motion with document visibility', () => {
    let visibilityState: DocumentVisibilityState = 'visible'
    vi.spyOn(document, 'visibilityState', 'get').mockImplementation(() => visibilityState)

    const { result } = renderHook(useLandingPage)
    expect(result.current.isDocumentVisible).toBe(true)

    visibilityState = 'hidden'
    act(() => document.dispatchEvent(new Event('visibilitychange')))
    expect(result.current.isDocumentVisible).toBe(false)

    visibilityState = 'visible'
    act(() => document.dispatchEvent(new Event('visibilitychange')))
    expect(result.current.isDocumentVisible).toBe(true)
  })
})
