import { useEffect, useSyncExternalStore } from 'react'

// The key of the activity question on screen, so the Mentor can tell which one
// "this question" means. Only the activity page writes it.
let screenQuestion: string | null = null
const listeners = new Set<() => void>()

function setScreenQuestion(key: string | null) {
  if (screenQuestion === key) return
  screenQuestion = key
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function read() {
  return screenQuestion
}

export function useMentorScreenQuestion(): string | null {
  return useSyncExternalStore(subscribe, read, () => null)
}

export function useReportMentorScreenQuestion(key: string | null) {
  useEffect(() => {
    setScreenQuestion(key)
    return () => setScreenQuestion(null)
  }, [key])
}
