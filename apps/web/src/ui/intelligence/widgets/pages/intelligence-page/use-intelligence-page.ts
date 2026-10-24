import { useNavigate, useSearch } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'

import { ROUTES } from '@/constants/routes'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

const REVEAL_FOCUS_TIMEOUT_MS = 3000

export function useIntelligencePage() {
  const navigate = useNavigate()
  const { session, message } = useSearch({ from: '/intelligence/' })
  const {
    selectedSessionId,
    selectSession,
    startNewConversation,
    isValidatingScope,
    sessionDetail,
    revealMessage,
  } = useMentorContext()
  const revealMessageRef = useRef(revealMessage)
  revealMessageRef.current = revealMessage
  const handledMessageId = useRef<string | null>(null)
  const [pendingFocusMessageId, setPendingFocusMessageId] = useState<string | null>(null)
  const lastRouteSession = useRef(session)
  const hasInitializedRoute = useRef(false)
  const routeGeneration = useRef(0)
  const isLoadingRoute = useRef(false)
  const [isPageReady, setIsPageReady] = useState(!session)

  useEffect(() => {
    if (isValidatingScope) return
    const routeChanged = lastRouteSession.current !== session
    const firstRouteRead = !hasInitializedRoute.current
    hasInitializedRoute.current = true

    if (firstRouteRead || routeChanged) {
      lastRouteSession.current = session
      const generation = ++routeGeneration.current
      isLoadingRoute.current = false
      if (session && session !== selectedSessionId) {
        isLoadingRoute.current = true
        setIsPageReady(false)
        void selectSession(session).finally(() => {
          if (generation === routeGeneration.current) {
            isLoadingRoute.current = false
            setIsPageReady(true)
          }
        })
        return
      }
      if (routeChanged && !session && selectedSessionId) {
        startNewConversation()
        setIsPageReady(true)
        return
      }
    }

    if (isLoadingRoute.current) return
    setIsPageReady(true)
    if (session !== selectedSessionId) {
      void navigate({
        to: ROUTES.intelligence,
        search: {
          session: selectedSessionId ?? undefined,
          message: session ? message : undefined,
        },
        replace: true,
      })
    }
  }, [
    isValidatingScope,
    message,
    navigate,
    selectSession,
    selectedSessionId,
    session,
    startNewConversation,
  ])

  const isConversationLoaded =
    isPageReady &&
    !isValidatingScope &&
    Boolean(session) &&
    selectedSessionId === session &&
    sessionDetail?.session.id === session

  // biome-ignore lint/correctness/useExhaustiveDependencies: the reveal runs once per message of the loaded conversation.
  useEffect(
    function revealOriginMessage() {
      if (!message) {
        handledMessageId.current = null
        return
      }
      if (!isConversationLoaded || handledMessageId.current === message) return
      handledMessageId.current = message
      void revealMessageRef.current(message).then((wasFound) => {
        if (wasFound) setPendingFocusMessageId(message)
        else void clearMessageFromUrl()
      })
    },
    [isConversationLoaded, message],
  )

  // biome-ignore lint/correctness/useExhaustiveDependencies: focus follows the revealed messages list.
  useEffect(
    function focusRevealedMessage() {
      if (!pendingFocusMessageId) return
      const target = document.querySelector<HTMLElement>(
        `[data-message-id="${pendingFocusMessageId}"]`,
      )
      if (!target) return
      if (typeof target.scrollIntoView === 'function')
        target.scrollIntoView({ block: 'center' })
      target.focus()
      setPendingFocusMessageId(null)
      void clearMessageFromUrl()
    },
    [pendingFocusMessageId, sessionDetail?.messages.items, isPageReady],
  )

  // biome-ignore lint/correctness/useExhaustiveDependencies: an unresolved reveal only waits for the timeout.
  useEffect(
    function releaseUnresolvedReveal() {
      if (!pendingFocusMessageId) return
      const timer = window.setTimeout(() => {
        setPendingFocusMessageId(null)
        void clearMessageFromUrl()
      }, REVEAL_FOCUS_TIMEOUT_MS)
      return () => window.clearTimeout(timer)
    },
    [pendingFocusMessageId],
  )

  function clearMessageFromUrl() {
    return navigate({
      to: ROUTES.intelligence,
      search: { session, message: undefined },
      replace: true,
    })
  }

  return { isPageReady }
}
