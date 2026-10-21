import { cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useMentorFab } from '../use-mentor-fab'

vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
const useMentorContextMock = vi.mocked(useMentorContext)

describe('useMentorFab', () => {
  afterEach(cleanup)

  it('traps Tab at the panel boundary and restores focus to the trigger after close', () => {
    const trigger = document.createElement('button')
    const panel = document.createElement('div')
    panel.tabIndex = -1
    const first = document.createElement('button')
    const last = document.createElement('button')
    panel.append(first, last)
    document.body.append(trigger, panel)
    const closePanel = vi.fn()
    let isPanelOpen = true
    useMentorContextMock.mockImplementation(
      () =>
        ({
          closePanel,
          isPanelOpen,
          openPanel: vi.fn(),
        }) as unknown as ReturnType<typeof useMentorContext>,
    )

    const { result, rerender } = renderHook(() => useMentorFab())
    result.current.triggerRef.current = trigger
    result.current.panelRef.current = panel
    last.focus()
    const preventDefault = vi.fn()
    result.current.handlePanelKeyDown({
      key: 'Tab',
      shiftKey: false,
      preventDefault,
    } as unknown as React.KeyboardEvent<HTMLDivElement>)
    expect(first).toHaveFocus()
    expect(preventDefault).toHaveBeenCalledOnce()

    result.current.handlePanelKeyDown({
      key: 'Escape',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent<HTMLDivElement>)
    expect(closePanel).toHaveBeenCalledOnce()
    isPanelOpen = false
    rerender()
    expect(trigger).toHaveFocus()
    trigger.remove()
    panel.remove()
  })

  it('focuses the panel on open and handles reverse and empty-panel tab boundaries', () => {
    const panel = document.createElement('div')
    panel.tabIndex = -1
    const trigger = document.createElement('button')
    const first = document.createElement('button')
    const last = document.createElement('button')
    panel.append(first, last)
    document.body.append(trigger, panel)
    let isPanelOpen = false
    useMentorContextMock.mockImplementation(
      () =>
        ({
          closePanel: vi.fn(),
          isPanelOpen,
          openPanel: vi.fn(),
        }) as unknown as ReturnType<typeof useMentorContext>,
    )
    const { result, rerender } = renderHook(() => useMentorFab())
    result.current.panelRef.current = panel
    result.current.triggerRef.current = trigger
    isPanelOpen = true
    rerender()
    expect(first).toHaveFocus()

    first.focus()
    const preventDefault = vi.fn()
    result.current.handlePanelKeyDown({
      key: 'Tab',
      shiftKey: true,
      preventDefault,
    } as unknown as React.KeyboardEvent<HTMLDivElement>)
    expect(last).toHaveFocus()
    expect(preventDefault).toHaveBeenCalledOnce()

    panel.replaceChildren()
    const emptyPreventDefault = vi.fn()
    result.current.handlePanelKeyDown({
      key: 'Tab',
      shiftKey: false,
      preventDefault: emptyPreventDefault,
    } as unknown as React.KeyboardEvent<HTMLDivElement>)
    expect(panel).toHaveFocus()
    expect(emptyPreventDefault).toHaveBeenCalledOnce()

    const nonTabPreventDefault = vi.fn()
    result.current.handlePanelKeyDown({
      key: 'ArrowLeft',
      shiftKey: false,
      preventDefault: nonTabPreventDefault,
    } as unknown as React.KeyboardEvent<HTMLDivElement>)
    expect(nonTabPreventDefault).not.toHaveBeenCalled()
    panel.remove()
    trigger.remove()
  })
  it('closes a previously opened panel when entering the dedicated Mentor page', () => {
    const closePanel = vi.fn()
    useMentorContextMock.mockReturnValue({
      closePanel,
      isPanelOpen: true,
      openPanel: vi.fn(),
    } as unknown as ReturnType<typeof useMentorContext>)
    const { rerender } = renderHook(({ isMentorPage }) => useMentorFab(isMentorPage), {
      initialProps: { isMentorPage: false },
    })
    expect(closePanel).not.toHaveBeenCalled()
    rerender({ isMentorPage: true })
    expect(closePanel).toHaveBeenCalledOnce()
  })
})
