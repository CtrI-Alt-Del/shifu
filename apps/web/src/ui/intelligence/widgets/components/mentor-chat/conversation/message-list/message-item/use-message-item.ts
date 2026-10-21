import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from 'motion/react'
import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import type { MentorMessage } from '@/rest/services/intelligence-service'
import type { IconName } from '@/ui/shared/widgets/components/icon'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useMentorAttachmentFileQuery } from '@/ui/intelligence/hooks/use-mentor-attachment-file-query'
import type { MentorAttachment } from '@/core/intelligence/mentor-attachment'
import type { MentorAttachmentSourceView } from './sources'

const MESSAGE_TIME_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'America/Sao_Paulo',
})

export function useMessageItem(
  message: MentorMessage,
  response?: MentorResponseSnapshot | null,
) {
  const mentor = useMentorContext()
  const [requestedSource, setRequestedSource] = useState<{
    messageId: string
    attachmentIds: string[]
  } | null>(null)
  const currentSession = mentor.selectedSessionId === message.sessionId
  const imageAttachments = currentSession
    ? message.attachments.filter(
        (attachment) =>
          attachment.mediaType.startsWith('image/') &&
          ['ready', 'partial'].includes(attachment.status),
      )
    : []
  const requestedAttachmentIds =
    requestedSource?.messageId === message.id ? requestedSource.attachmentIds : []
  const sourceLearnerMessage =
    currentSession && response
      ? mentor.sessionDetail?.messages.items.find(
          (candidate) =>
            candidate.id === response.learnerMessageId &&
            candidate.sessionId === message.sessionId &&
            candidate.role === 'learner',
        )
      : null
  const sourceAttachments = new Map(
    (sourceLearnerMessage?.attachments ?? []).map((attachment) => [
      attachment.attachmentId,
      attachment,
    ]),
  )
  const sourceViewsByBlock = new Map<string, MentorAttachmentSourceView[]>()
  for (const block of response?.blocks ?? []) {
    for (const source of block.sources ?? []) {
      const attachment = sourceAttachments.get(source.attachmentId)
      if (!attachment || !['ready', 'partial'].includes(attachment.status)) continue
      const existing = sourceViewsByBlock.get(block.blockKey) ?? []
      existing.push({ source, attachment, url: null, error: null })
      sourceViewsByBlock.set(block.blockKey, existing)
    }
  }
  const requestedSourceAttachments = [...sourceAttachments.values()].filter(
    (attachment) => requestedAttachmentIds.includes(attachment.attachmentId),
  )
  const { mentorAttachmentFiles, mentorAttachmentFileErrors } =
    useMentorAttachmentFileQuery({
      sessionId: currentSession ? message.sessionId : null,
      attachmentIds: [
        ...imageAttachments.map((attachment) => attachment.attachmentId),
        ...requestedSourceAttachments.map((attachment) => attachment.attachmentId),
      ],
      previewAttachmentIds: [
        ...imageAttachments.map((attachment) => attachment.attachmentId),
        ...requestedSourceAttachments
          .filter((attachment) => attachment.mediaType.startsWith('image/'))
          .map((attachment) => attachment.attachmentId),
      ],
    })
  const [attachmentUrls, setAttachmentUrls] = useState<Record<string, string>>({})
  const shouldReduceMotion = useReducedMotion()
  const [initialBlockAnimations] = useState(
    () =>
      new Map(
        response?.blocks.map((block) => [
          `${response.attemptId}:${block.blockKey}`,
          mentor.shouldAnimateBlock(response.attemptId, block.blockKey),
        ]),
      ),
  )
  const shouldAnimateEntrance =
    !response || [...initialBlockAnimations.values()].some(Boolean)
  const [isCopied, setIsCopied] = useState(false)
  const [copyError, setCopyError] = useState(false)
  const [visibleLength, setVisibleLength] = useState<Record<string, number>>({})
  const presentations = useRef(new Map<string, { content: string; timer?: number }>())
  const copiedTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const copyContent = response
    ? response.blocks.map((block) => block.content).join('\n\n')
    : message.content
  const createdAt = message.createdAt ? new Date(message.createdAt) : null
  const timeLabel =
    createdAt && !Number.isNaN(createdAt.valueOf())
      ? MESSAGE_TIME_FORMATTER.format(createdAt)
      : null
  const isLearnerMessage = message.role === 'learner'
  const isMentorMessage = message.role === 'mentor'
  const speakerLabel = isMentorMessage ? 'Mentor' : null
  const copyLabel = isCopied ? 'Copiada' : 'Copiar'
  const copyAccessibleLabel = isCopied ? 'Mensagem copiada' : 'Copiar mensagem'
  const copyIconName: IconName = isCopied ? 'circle-check' : 'copy'

  useEffect(
    () => () => {
      for (const presentation of presentations.current.values()) {
        if (presentation.timer !== undefined) window.clearInterval(presentation.timer)
      }
      presentations.current.clear()
      if (copiedTimeout.current) clearTimeout(copiedTimeout.current)
    },
    [],
  )
  useEffect(() => {
    const nextUrls: Record<string, string> = {}
    for (const [attachmentId, blob] of Object.entries(mentorAttachmentFiles)) {
      nextUrls[attachmentId] = URL.createObjectURL(blob)
    }
    setAttachmentUrls(nextUrls)
    return () => {
      for (const url of Object.values(nextUrls)) URL.revokeObjectURL(url)
    }
  }, [mentorAttachmentFiles])
  useEffect(() => {
    if (!response) return
    const reducedMotion =
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    for (const block of response.blocks) {
      const key = `${response.attemptId}:${block.blockKey}`
      const existing = presentations.current.get(key)
      if (existing?.content === block.content) continue
      if (existing?.timer !== undefined) window.clearInterval(existing.timer)
      const presentation: { content: string; timer?: number } = { content: block.content }
      presentations.current.set(key, presentation)
      const shouldAnimate =
        (initialBlockAnimations.get(key) ??
          mentor.shouldAnimateBlock(response.attemptId, block.blockKey)) &&
        !reducedMotion
      mentor.markBlockPresented(response.attemptId, block.blockKey)
      if (!shouldAnimate) {
        setVisibleLength((current) => ({ ...current, [key]: block.content.length }))
        continue
      }
      let length = 0
      setVisibleLength((current) => ({ ...current, [key]: 0 }))
      const timer = window.setInterval(() => {
        length = Math.min(block.content.length, length + 8)
        setVisibleLength((current) => ({ ...current, [key]: length }))
        if (length === block.content.length) window.clearInterval(timer)
      }, 20)
      presentation.timer = timer
    }
  }, [
    response?.attemptId,
    response,
    mentor.shouldAnimateBlock,
    mentor.markBlockPresented,
    initialBlockAnimations,
  ])
  const blocks =
    response?.blocks.map((block) => {
      const length = visibleLength[`${response.attemptId}:${block.blockKey}`]
      return {
        ...block,
        isTyping: length !== undefined && length < block.content.length,
        displayedContent:
          length === undefined ? block.content : block.content.slice(0, length),
        sources: (sourceViewsByBlock.get(block.blockKey) ?? []).map((item) => ({
          ...item,
          url: valueOrNull(attachmentUrls, item.attachment.attachmentId),
          error: errorMessageOrNull(
            mentorAttachmentFileErrors[item.attachment.attachmentId],
          ),
        })),
      }
    }) ?? []
  const attachments = currentSession
    ? message.attachments.map((attachment: MentorAttachment) => ({
        attachment,
        url: valueOrNull(attachmentUrls, attachment.attachmentId),
        error: errorMessageOrNull(mentorAttachmentFileErrors[attachment.attachmentId]),
      }))
    : []
  function handleOpenAttachment(attachmentId: string) {
    setRequestedSource({ messageId: message.id, attachmentIds: [attachmentId] })
  }
  async function handleCopyMessage() {
    setCopyError(false)
    try {
      await navigator.clipboard.writeText(copyContent)
      if (copiedTimeout.current) clearTimeout(copiedTimeout.current)
      setIsCopied(true)
      copiedTimeout.current = setTimeout(() => setIsCopied(false), 2000)
    } catch {
      setIsCopied(false)
      setCopyError(true)
    }
  }

  return {
    blocks,
    attachments,
    handleOpenAttachment,
    shouldAnimateEntrance,
    shouldReduceMotion,
    copyAccessibleLabel,
    copyContent,
    copyError,
    copyIconName,
    copyLabel,
    hasResponse: Boolean(response),
    isCopied,
    isLearnerMessage,
    isMentorMessage,
    speakerLabel,
    timeLabel,
    visibleLength,
    handleCopyMessage,
  }
}
function valueOrNull(values: Record<string, string>, key: string): string | null {
  return values[key] || null
}
function errorMessageOrNull(error: { message: string } | undefined): string | null {
  return error?.message || null
}
