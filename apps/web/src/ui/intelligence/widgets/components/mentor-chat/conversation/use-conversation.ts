import { useEffect, useLayoutEffect, useRef } from 'react'

import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export const useConversation = () => {
  const mentor = useMentorContext()
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const previousScrollHeight = useRef(0)
  const wasLoadingOlder = useRef(false)
  const previousMessageCount = useRef(0)
  const renderedSessionId = useRef<string | null>(null)
  const messageCount = mentor.sessionDetail?.messages.items.length ?? 0

  const handleScroll = () => {
    const element = scrollRef.current
    if (
      element &&
      element.scrollTop < 48 &&
      mentor.sessionDetail?.messages.nextCursor &&
      !mentor.isReadingMessages
    ) {
      previousScrollHeight.current = element.scrollHeight
      wasLoadingOlder.current = true
      void mentor.loadOlderMessages()
    }
  }

  useLayoutEffect(() => {
    const element = scrollRef.current
    const sessionId = mentor.sessionDetail?.session.id ?? null
    if (sessionId !== renderedSessionId.current) {
      renderedSessionId.current = sessionId
      if (element && sessionId) element.scrollTop = element.scrollHeight
      previousMessageCount.current = messageCount
      return
    }
    if (
      element &&
      wasLoadingOlder.current &&
      messageCount > previousMessageCount.current
    ) {
      element.scrollTop += element.scrollHeight - previousScrollHeight.current
      wasLoadingOlder.current = false
    }
    previousMessageCount.current = messageCount
  })

  useEffect(() => {
    const element = scrollRef.current
    if (!mentor.selectedSessionId && element) {
      if (typeof element.scrollTo === 'function') element.scrollTo({ top: 0 })
      else element.scrollTop = 0
    }
  }, [mentor.selectedSessionId])

  return { ...mentor, handleScroll, scrollRef }
}
