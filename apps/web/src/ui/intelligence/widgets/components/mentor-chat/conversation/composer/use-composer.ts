import {
  useEffect,
  useLayoutEffect,
  useRef,
  type FormEvent,
  type KeyboardEvent,
} from 'react'

import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export const useComposer = (surface: 'page' | 'fab' = 'fab') => {
  const mentor = useMentorContext()
  const placeholder = mentor.isSummarizingContext
    ? 'Aguarde enquanto o contexto é resumido'
    : 'Pergunte ao Mentor…'
  const previousDictationStatus = useRef(mentor.dictationStatus)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  // The controlled draft and a wrapping placeholder change scrollHeight after React updates the textarea.
  // biome-ignore lint/correctness/useExhaustiveDependencies: resize on every draft or placeholder update, including clears.
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
  }, [mentor.draft, placeholder])
  const { releaseDictationSurface, dictationStatus, draft } = mentor
  const draftAttachments = mentor.draftAttachments ?? []
  useEffect(
    () => () => releaseDictationSurface?.(surface),
    [releaseDictationSurface, surface],
  )
  // biome-ignore lint/correctness/useExhaustiveDependencies: focus follows the applied draft update.
  useLayoutEffect(() => {
    if (dictationStatus === 'review' && previousDictationStatus.current !== 'review')
      textareaRef.current?.focus()
    previousDictationStatus.current = dictationStatus
  }, [dictationStatus, draft])
  const hasAcceptedSession = Boolean(mentor.selectedSessionId)
  const isResponsePending = Boolean(mentor.sessionDetail?.pendingLearnerMessageId)
  const canSend =
    (Boolean(mentor.draft.trim()) || draftAttachments.length > 0) &&
    !mentor.isSubmittingFirstMessage &&
    !isResponsePending &&
    !mentor.isDictationBusy &&
    !mentor.isPreparingAttachments &&
    draftAttachments.every(
      ({ attachment, error }) =>
        !error && attachment && ['ready', 'partial'].includes(attachment.status),
    )
  const canManageAttachments =
    !mentor.isSubmittingFirstMessage && !isResponsePending && !mentor.isDictationBusy

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
    canManageAttachments,
    draftAttachments,
    handleKeyDown,
    isResponsePending,
    handleSubmit,
    hasAcceptedSession,
    placeholder,
    textareaRef,
  }
}
