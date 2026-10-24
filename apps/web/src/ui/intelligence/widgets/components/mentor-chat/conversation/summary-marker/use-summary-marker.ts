import { useEffect, useRef, useState } from 'react'

import type { MentorSummaryMarker } from '@/core/intelligence/mentor-session-summary'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

import { useMentorSessionSummaryQuery } from './use-mentor-session-summary-query'

const REVEAL_FOCUS_TIMEOUT_MS = 3000

export type SummaryMarkerProps =
  | { variant: 'ready'; marker: MentorSummaryMarker }
  | { variant: 'processing' }
  | { variant: 'failed' }

export function useSummaryMarker(props: SummaryMarkerProps) {
  const { selectedSessionId, sessionDetail, revealMessage } = useMentorContext()
  const marker = props.variant === 'ready' ? props.marker : null
  const [isOpen, setIsOpen] = useState(false)
  const [hasOpened, setHasOpened] = useState(false)
  const [pendingFocusMessageId, setPendingFocusMessageId] = useState<string | null>(null)
  const rootRef = useRef<HTMLDivElement | null>(null)
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const isRevealing = useRef(false)
  const { summaryContent, summaryError, isLoadingSummary, refetchSummary } =
    useMentorSessionSummaryQuery({
      sessionId: selectedSessionId,
      version: marker?.version ?? null,
      isEnabled: hasOpened,
    })
  const summaryText = summaryContent?.text ?? null
  const hasSummaryError = Boolean(summaryError) && !summaryContent

  // biome-ignore lint/correctness/useExhaustiveDependencies: focus follows the revealed messages list.
  useEffect(
    function focusRevealedMessage() {
      if (!pendingFocusMessageId) return
      const container = rootRef.current?.closest('section') ?? document
      const target = container.querySelector<HTMLElement>(
        `[data-message-id="${pendingFocusMessageId}"]`,
      )
      if (!target) return
      if (typeof target.scrollIntoView === 'function')
        target.scrollIntoView({ block: 'center' })
      target.focus()
      isRevealing.current = false
      setPendingFocusMessageId(null)
    },
    [pendingFocusMessageId, sessionDetail?.messages.items],
  )

  useEffect(
    function releaseUnresolvedReveal() {
      if (!pendingFocusMessageId) return
      const timer = window.setTimeout(() => {
        isRevealing.current = false
        setPendingFocusMessageId(null)
        triggerRef.current?.focus()
      }, REVEAL_FOCUS_TIMEOUT_MS)
      return () => window.clearTimeout(timer)
    },
    [pendingFocusMessageId],
  )

  function handleOpenChange(open: boolean) {
    setIsOpen(open)
    if (open) {
      isRevealing.current = false
      setHasOpened(true)
    }
  }

  function handleCloseAutoFocus(event: Event) {
    if (isRevealing.current) event.preventDefault()
  }

  async function handleRevealOriginals() {
    if (!summaryContent || isRevealing.current) return
    const { firstMessageId } = summaryContent
    isRevealing.current = true
    setIsOpen(false)
    const wasFound = await revealMessage(firstMessageId)
    if (wasFound) setPendingFocusMessageId(firstMessageId)
    else {
      isRevealing.current = false
      triggerRef.current?.focus()
    }
  }

  function handleRetry() {
    void refetchSummary()
  }

  return {
    isOpen,
    summaryText,
    isLoadingSummary,
    hasSummaryError,
    rootRef,
    triggerRef,
    handleOpenChange,
    handleCloseAutoFocus,
    handleRevealOriginals,
    handleRetry,
  }
}
