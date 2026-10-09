import { useNavigate, useSearch } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'

import { ROUTES } from '@/constants/routes'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export function useIntelligencePage() {
  const navigate = useNavigate()
  const { session } = useSearch({ from: '/intelligence/' })
  const { selectedSessionId, selectSession, startNewConversation, isValidatingScope } =
    useMentorContext()
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
        search: { session: selectedSessionId ?? undefined },
        replace: true,
      })
    }
  }, [
    isValidatingScope,
    navigate,
    selectSession,
    selectedSessionId,
    session,
    startNewConversation,
  ])

  return { isPageReady }
}
