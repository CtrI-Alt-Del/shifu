import { act, fireEvent, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useMobileHeader } from '../use-mobile-header'

describe('useMobileHeader', () => {
  it('toggles the menu and closes it after navigation', () => {
    const { result } = renderHook(() => useMobileHeader())

    expect(result.current.isMenuOpen).toBe(false)
    act(() => result.current.handleMenuToggle())
    expect(result.current.isMenuOpen).toBe(true)
    act(() => result.current.handleNavigation())
    expect(result.current.isMenuOpen).toBe(false)
  })

  it('closes an open menu when Escape is pressed', () => {
    const { result } = renderHook(() => useMobileHeader())

    act(() => result.current.handleMenuToggle())
    fireEvent.keyDown(document, { key: 'Escape' })

    expect(result.current.isMenuOpen).toBe(false)
  })

  it('ignores inside pointers and closes on an outside pointer', () => {
    const { result } = renderHook(() => useMobileHeader())
    const menu = document.createElement('div')
    document.body.append(menu)
    result.current.menuRef.current = menu

    act(() => result.current.handleMenuToggle())
    fireEvent.pointerDown(menu)
    expect(result.current.isMenuOpen).toBe(true)

    fireEvent.pointerDown(document.body)
    expect(result.current.isMenuOpen).toBe(false)
    menu.remove()
  })
})
