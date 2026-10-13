import { useLayoutEffect, useRef, type FormEvent, type KeyboardEvent } from 'react'

import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export const useComposer = (surface: 'page' | 'fab' = 'fab') => {
  const mentor = useMentorContext()
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  // The controlled draft changes scrollHeight after React updates the textarea.
  // biome-ignore lint/correctness/useExhaustiveDependencies: resize on every draft update, including clears.
  useLayoutEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    const resize = () => {
      textarea.style.height = 'auto'
      textarea.style.height = `${textarea.scrollHeight}px`
    }
    resize()

    if (typeof ResizeObserver === 'undefined') return
    let previousWidth = textarea.clientWidth
    const observer = new ResizeObserver(() => {
      if (textarea.clientWidth === previousWidth) return
      previousWidth = textarea.clientWidth
      resize()
    })
    observer.observe(textarea)
    return () => observer.disconnect()
  }, [mentor.draft])
  const hasAcceptedSession = Boolean(mentor.selectedSessionId)
  const isResponsePending = Boolean(mentor.sessionDetail?.pendingLearnerMessageId)
  const canSend =
    Boolean(mentor.draft.trim()) && !mentor.isSubmittingFirstMessage && !isResponsePending

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (canSend) void mentor.sendFirstMessage(surface)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return

    event.preventDefault()
    if (canSend) event.currentTarget.form?.requestSubmit()
  }

  return {
    ...mentor,
    canSend,
    handleKeyDown,
    isResponsePending,
    handleSubmit,
    hasAcceptedSession,
    textareaRef,
  }
}
