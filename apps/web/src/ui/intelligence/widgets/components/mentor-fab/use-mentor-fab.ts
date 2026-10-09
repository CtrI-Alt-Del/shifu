import { useEffect, useRef, type KeyboardEvent } from 'react'

import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export const useMentorFab = (isMentorPage = false) => {
  const {
    activeDialog,
    closePanel,
    isPanelOpen,
    openPanel,
    panelView,
    isValidatingScope,
    selectedSessionId,
  } = useMentorContext()
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)
  const wasOpen = useRef(false)

  // biome-ignore lint/correctness/useExhaustiveDependencies: restore focus after panel content replaces the focused control.
  useEffect(() => {
    if (isMentorPage && isPanelOpen) {
      closePanel()
      return
    }
    if (
      isPanelOpen &&
      !activeDialog &&
      (!wasOpen.current || !panelRef.current?.contains(document.activeElement))
    ) {
      const firstControl = panelRef.current?.querySelector<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled])',
      )
      ;(firstControl ?? panelRef.current)?.focus()
    } else if (!isPanelOpen && wasOpen.current) {
      triggerRef.current?.focus()
    }
    wasOpen.current = isPanelOpen
  }, [
    activeDialog,
    closePanel,
    isMentorPage,
    isPanelOpen,
    panelView,
    isValidatingScope,
    selectedSessionId,
  ])

  const handlePanelKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape' && !event.defaultPrevented) {
      event.preventDefault()
      closePanel()
      return
    }
    if (event.key !== 'Tab' || !panelRef.current) return
    const focusable = Array.from(
      panelRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      ),
    )
    if (!focusable.length) {
      event.preventDefault()
      panelRef.current.focus()
      return
    }
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last?.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first?.focus()
    }
  }

  return { closePanel, handlePanelKeyDown, isPanelOpen, openPanel, panelRef, triggerRef }
}
