import { useEffect, useLayoutEffect, useRef } from 'react'

import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export const useConversation = () => {
  const mentor = useMentorContext()
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const previousScrollHeight = useRef(0)
  const wasLoadingOlder = useRef(false)
  const previousMessageCount = useRef(0)
  const previousResponseContent = useRef<string | null>(null)
  const isAtBottom = useRef(true)
  const renderedSessionId = useRef<string | null>(null)
  const messages = mentor.sessionDetail?.messages.items ?? []
  const messageCount = messages.length
  const response = mentor.response
  const visibleMessages = response?.blocks.length
    ? messages.filter(
        (message) =>
          message.role !== 'mentor' ||
          message.inReplyToMessageId !== response.learnerMessageId,
      )
    : messages
  const responseContent = mentor.response
    ? `${mentor.response.attemptId}:${mentor.response.blocks.map((block) => `${block.blockKey}:${block.content}`).join('|')}`
    : null

  const handleScroll = () => {
    const element = scrollRef.current
    if (element) {
      isAtBottom.current =
        element.scrollHeight - element.scrollTop - element.clientHeight <= 48
    }
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
      previousResponseContent.current = responseContent
      isAtBottom.current = true
      return
    }
    if (
      element &&
      wasLoadingOlder.current &&
      messageCount > previousMessageCount.current
    ) {
      element.scrollTop += element.scrollHeight - previousScrollHeight.current
      wasLoadingOlder.current = false
      isAtBottom.current = false
    } else if (
      element &&
      !wasLoadingOlder.current &&
      (messageCount > previousMessageCount.current ||
        responseContent !== previousResponseContent.current) &&
      (isAtBottom.current ||
        mentor.sessionDetail?.messages.items.at(-1)?.role === 'learner')
    ) {
      element.scrollTop = element.scrollHeight
      isAtBottom.current = true
    }
    previousMessageCount.current = messageCount
    previousResponseContent.current = responseContent
  })

  useEffect(() => {
    const element = scrollRef.current
    if (!mentor.selectedSessionId && element) {
      if (typeof element.scrollTo === 'function') element.scrollTo({ top: 0 })
      else element.scrollTop = 0
    }
  }, [mentor.selectedSessionId])

  return { ...mentor, handleScroll, scrollRef, visibleMessages }
}
