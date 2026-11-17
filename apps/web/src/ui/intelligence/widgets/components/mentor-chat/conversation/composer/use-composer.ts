import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from 'react'

import { useAiQuotaBlock } from '@/ui/intelligence/hooks/use-ai-quota-block'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

const BLOCKED_PLACEHOLDER = 'Envio pausado até a renovação da cota'
const BLOCKED_PLACEHOLDER_SHORT = 'Envio pausado'
/** Below this field width the long blocked placeholder would wrap onto two lines. */
const NARROW_FIELD_WIDTH = 320

export const useComposer = (surface: 'page' | 'fab' = 'fab') => {
  const mentor = useMentorContext()
  const {
    isAiQuotaBlocked,
    isAiQuotaNearLimit,
    getAiQuotaBlockedMessage,
    aiQuotaBlockedRole,
    aiQuotaAccountId,
    aiQuotaPercentage,
    aiQuotaRenewsOn,
  } = useAiQuotaBlock(mentor.isAiQuotaRefused)
  const aiQuotaBlockedMessage = getAiQuotaBlockedMessage('mentor')
  const [isNarrowField, setIsNarrowField] = useState(false)
  const placeholder = isAiQuotaBlocked
    ? isNarrowField
      ? BLOCKED_PLACEHOLDER_SHORT
      : BLOCKED_PLACEHOLDER
    : mentor.isSummarizingContext
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
    // An unmeasured field (width 0) keeps the long text.
    const trackNarrowness = () =>
      setIsNarrowField(
        textarea.clientWidth > 0 && textarea.clientWidth < NARROW_FIELD_WIDTH,
      )
    resize()
    trackNarrowness()

    if (typeof ResizeObserver === 'undefined') return
    let previousWidth = textarea.clientWidth
    const observer = new ResizeObserver(() => {
      if (textarea.clientWidth === previousWidth) return
      previousWidth = textarea.clientWidth
      resize()
      trackNarrowness()
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
  const isActionBlocked = Boolean(mentor.blockingActionProposalId)
  const canStartDictation =
    mentor.canStartDictation && !isActionBlocked && !isAiQuotaBlocked
  const canSend =
    (Boolean(mentor.draft.trim()) || draftAttachments.length > 0) &&
    !isAiQuotaBlocked &&
    !mentor.isSubmittingFirstMessage &&
    !isResponsePending &&
    !isActionBlocked &&
    !mentor.isDictationBusy &&
    !mentor.isPreparingAttachments &&
    draftAttachments.every(
      ({ attachment, error }) =>
        !error && attachment && ['ready', 'partial'].includes(attachment.status),
    )
  const canManageAttachments =
    !mentor.isSubmittingFirstMessage &&
    !isResponsePending &&
    !isActionBlocked &&
    !mentor.isDictationBusy

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
    canStartDictation,
    draftAttachments,
    handleKeyDown,
    isActionBlocked,
    isAiQuotaBlocked,
    isAiQuotaNearLimit,
    aiQuotaBlockedMessage,
    aiQuotaBlockedRole,
    aiQuotaAccountId,
    aiQuotaPercentage,
    aiQuotaRenewsOn,
    isResponsePending,
    handleSubmit,
    hasAcceptedSession,
    placeholder,
    textareaRef,
  }
}
