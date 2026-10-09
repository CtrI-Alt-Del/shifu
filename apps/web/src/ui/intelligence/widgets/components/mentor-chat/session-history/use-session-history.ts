import { useEffect, useRef } from 'react'

import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export const useSessionHistory = () => {
  const mentor = useMentorContext()
  const listRef = useRef<HTMLUListElement | null>(null)
  const loadSentinelRef = useRef<HTMLLIElement | null>(null)

  useEffect(() => {
    const sentinel = loadSentinelRef.current
    if (!sentinel || !('IntersectionObserver' in window)) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) void mentor.loadMoreSessions()
      },
      { root: listRef.current, rootMargin: '160px' },
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [mentor.loadMoreSessions])

  return { ...mentor, listRef, loadSentinelRef }
}
