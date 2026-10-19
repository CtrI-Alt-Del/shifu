import type {
  MentorContextHint,
  MentorResponseEvent,
  MentorResponseSnapshot,
  SubmitMentorMessageInput,
} from '@/core/intelligence/mentor-response'
import type { MentorAttachment } from '@/core/intelligence/mentor-attachment'
import { NativeMentorEventSource } from '@/provision/realtime/native-mentor-event-source'
import { useMentorResponseStream } from '@/ui/intelligence/hooks/use-mentor-response-stream'
import { useSubmitMentorMessageAction } from '@/ui/intelligence/hooks/use-submit-mentor-message-action'
import { useCancelMentorResponseAction } from '@/ui/intelligence/hooks/use-cancel-mentor-response-action'
import { useRetryMentorResponseAction } from '@/ui/intelligence/hooks/use-retry-mentor-response-action'
import { useLocation, useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useRef, useState } from 'react'

import type {
  MentorSessionDetail,
  MentorSessionsPage,
} from '@/rest/services/intelligence-service'
import { ROUTES } from '@/constants/routes'
import { useCreateMentorSessionAction } from '@/ui/intelligence/hooks/use-create-mentor-session-action'
import { useCreateMentorAttachmentBatchAction } from '@/ui/intelligence/hooks/use-create-mentor-attachment-batch-action'
import { useUploadMentorAttachmentAction } from '@/ui/intelligence/hooks/use-upload-mentor-attachment-action'
import { useMentorAttachmentBatchQuery } from '@/ui/intelligence/hooks/use-mentor-attachment-batch-query'
import { useRemoveMentorAttachmentAction } from '@/ui/intelligence/hooks/use-remove-mentor-attachment-action'
import { useMentorSessionQuery } from '@/ui/intelligence/hooks/use-mentor-session-query'
import { useMentorSessionsQuery } from '@/ui/intelligence/hooks/use-mentor-sessions-query'
import { useRemoveMentorSessionAction } from '@/ui/intelligence/hooks/use-remove-mentor-session-action'
import { useRenameMentorSessionAction } from '@/ui/intelligence/hooks/use-rename-mentor-session-action'

import type { MentorContextValue, MentorDraftAttachment } from './types'
import { useSpeechRecognition } from '@/ui/shared/hooks/use-speech-recognition'

const SEARCH_DEBOUNCE_MS = 300
const MAX_MENTOR_ATTACHMENTS = 5
const MAX_MENTOR_ATTACHMENT_BYTES = 2_000_000
const EMPTY_SESSIONS_PAGE: MentorSessionsPage = { items: [], nextCursor: null }

export function useMentorContextProvider(
  accountEmail: string,
  contextHint: MentorContextHint | null = null,
): MentorContextValue {
  const { submitMentorMessage, isPending: isSubmittingMessage } =
    useSubmitMentorMessageAction(accountEmail)
  const { cancelMentorResponse, isPending: isCancellingResponse } =
    useCancelMentorResponseAction(accountEmail)
  const { retryMentorResponse, isPending: isRetryingResponse } =
    useRetryMentorResponseAction(accountEmail)
  const {
    status: dictationStatus,
    error: recognitionError,
    elapsedSeconds: dictationElapsedSeconds,
    languageAvailability: dictationLanguageAvailability,
    installationStatus: dictationInstallationStatus,
    installationError: dictationInstallationError,
    canInstallLanguage: canInstallDictationLanguage,
    startRecognition,
    finishRecognition,
    cancelRecognition,
    installLanguagePack,
  } = useSpeechRecognition('pt-BR', false)
  const [draftDictationError, setDraftDictationError] = useState<string | null>(null)
  const draftRevision = useRef(0)
  const installationTarget = useRef<{ surface: 'page' | 'fab' } | null>(null)
  const dictationTarget = useRef<{
    generation: number
    revision: number
    surface: 'page' | 'fab'
  } | null>(null)
  const cancelDictation = useCallback(
    function cancelDictation() {
      dictationTarget.current = null
      installationTarget.current = null
      cancelRecognition()
      setDraftDictationError(null)
    },
    [cancelRecognition],
  )
  const releaseDictationSurface = useCallback(
    function releaseDictationSurface(surface: 'page' | 'fab') {
      if (
        dictationTarget.current?.surface === surface ||
        installationTarget.current?.surface === surface
      )
        cancelDictation()
    },
    [cancelDictation],
  )
  const presentedBlocks = useRef(new Set<string>())
  const newBlocks = useRef(new Set<string>())
  const submissionHint = useRef<MentorContextHint | null>(null)
  const controlKeys = useRef(new Map<string, string>())
  const navigate = useNavigate()
  const location = useLocation()
  // biome-ignore lint/correctness/useExhaustiveDependencies: route/account changes invalidate the active dictation scope.
  useEffect(
    function cancelOnNavigation() {
      cancelDictation()
    },
    [cancelDictation, location.pathname, accountEmail],
  )
  const { readMentorSessions } = useMentorSessionsQuery(accountEmail)
  const { readMentorSession } = useMentorSessionQuery(accountEmail)
  const { createMentorSession, isCreatingMentorSession, resetCreateMentorSession } =
    useCreateMentorSessionAction(accountEmail)
  const { createMentorAttachmentBatch, resetCreateMentorAttachmentBatch } =
    useCreateMentorAttachmentBatchAction(accountEmail)
  const { uploadMentorAttachment } = useUploadMentorAttachmentAction()
  const { removeMentorAttachment } = useRemoveMentorAttachmentAction()
  const { isRenamingMentorSession, renameMentorSession, resetRenameMentorSession } =
    useRenameMentorSessionAction(accountEmail)
  const { isRemovingMentorSession, removeMentorSession, resetRemoveMentorSession } =
    useRemoveMentorSessionAction(accountEmail)

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [sessionDetail, setSessionDetail] = useState<MentorSessionDetail | null>(null)
  const [sessionsPage, setSessionsPage] = useState(EMPTY_SESSIONS_PAGE)
  const [draft, setDraft] = useState('')
  const [draftAttachments, setDraftAttachments] = useState<MentorDraftAttachment[]>([])
  const [attachmentBatchId, setAttachmentBatchId] = useState<string | null>(null)
  const [submissionKey, setSubmissionKey] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const [panelView, setPanelView] = useState<'conversation' | 'history'>('conversation')
  const [activeDialog, setActiveDialog] = useState<'rename' | 'remove' | null>(null)
  const [dialogSessionId, setDialogSessionId] = useState<string | null>(null)
  const [isValidatingScope, setIsValidatingScope] = useState(true)
  const [isReadingHistory, setIsReadingHistory] = useState(false)
  const [isReadingMessages, setIsReadingMessages] = useState(false)
  const [isReadingOlderMessages, setIsReadingOlderMessages] = useState(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [conversationError, setConversationError] = useState<string | null>(null)
  const [submissionError, setSubmissionError] = useState<string | null>(null)
  const [renameError, setRenameError] = useState<string | null>(null)
  const [removalError, setRemovalError] = useState<string | null>(null)
  const [scopeError, setScopeError] = useState<string | null>(null)
  const historyGeneration = useRef(0)
  const detailGeneration = useRef(0)
  const submissionMessage = useRef<string | null>(null)
  const submissionRunning = useRef(false)
  const attachmentGeneration = useRef(0)
  const draftAttachmentsRef = useRef(draftAttachments)
  draftAttachmentsRef.current = draftAttachments
  const attachmentBatchIdRef = useRef<string | null>(attachmentBatchId)
  attachmentBatchIdRef.current = attachmentBatchId
  const attachmentBatchCreation = useRef<Promise<string> | null>(null)

  const isPreparingAttachments = draftAttachments.some(
    (draftAttachment) =>
      !draftAttachment.error &&
      (!draftAttachment.attachment ||
        draftAttachment.attachment.status === 'uploading' ||
        draftAttachment.attachment.status === 'processing'),
  )
  const { mentorAttachmentBatch, mentorAttachmentBatchError } =
    useMentorAttachmentBatchQuery(accountEmail, attachmentBatchId, isPreparingAttachments)

  const updateDraftAttachments = useCallback(function updateDraftAttachments(
    update: (current: MentorDraftAttachment[]) => MentorDraftAttachment[],
  ) {
    const next = update(draftAttachmentsRef.current)
    draftAttachmentsRef.current = next
    setDraftAttachments(next)
  }, [])

  const clearDraftAttachments = useCallback(() => {
    attachmentGeneration.current += 1
    for (const attachment of draftAttachmentsRef.current) {
      if (attachment.previewUrl) URL.revokeObjectURL(attachment.previewUrl)
    }
    draftAttachmentsRef.current = []
    setDraftAttachments([])
    attachmentBatchIdRef.current = null
    attachmentBatchCreation.current = null
    setAttachmentBatchId(null)
    resetCreateMentorAttachmentBatch()
  }, [resetCreateMentorAttachmentBatch])

  useEffect(function releaseDraftAttachmentUrlsOnUnmount() {
    return () => {
      attachmentGeneration.current += 1
      for (const attachment of draftAttachmentsRef.current) {
        if (attachment.previewUrl) URL.revokeObjectURL(attachment.previewUrl)
      }
    }
  }, [])

  useEffect(
    function applyAttachmentBatchStatus() {
      if (!mentorAttachmentBatch || mentorAttachmentBatch.batchId !== attachmentBatchId)
        return
      updateDraftAttachments((current) =>
        current.map((draftAttachment) => {
          if (!draftAttachment.attachment) return draftAttachment
          const attachment = mentorAttachmentBatch.attachments.find(
            (candidate) =>
              candidate.attachmentId === draftAttachment.attachment?.attachmentId,
          )
          if (!attachment || attachment.status === 'removed') return draftAttachment
          if (
            isTerminalMentorAttachmentStatus(draftAttachment.attachment.status) &&
            attachment.status !== draftAttachment.attachment.status
          )
            return draftAttachment
          if (
            getMentorAttachmentStatusRank(attachment.status) <
            getMentorAttachmentStatusRank(draftAttachment.attachment.status)
          )
            return draftAttachment
          return {
            ...draftAttachment,
            attachment,
            error:
              attachment.status === 'failed'
                ? getMentorAttachmentFailureMessage(attachment)
                : null,
          }
        }),
      )
    },
    [attachmentBatchId, mentorAttachmentBatch, updateDraftAttachments],
  )

  useEffect(
    function markAttachmentBatchReadFailure() {
      if (!mentorAttachmentBatchError) return
      updateDraftAttachments((current) =>
        current.map((draftAttachment) =>
          draftAttachment.attachment &&
          ['uploading', 'processing'].includes(draftAttachment.attachment.status)
            ? {
                ...draftAttachment,
                error:
                  'Não foi possível acompanhar a preparação. Remova e adicione o arquivo novamente.',
              }
            : draftAttachment,
        ),
      )
    },
    [mentorAttachmentBatchError, updateDraftAttachments],
  )

  const clearPrivateState = useCallback(() => {
    cancelDictation()
    historyGeneration.current += 1
    detailGeneration.current += 1
    presentedBlocks.current.clear()
    newBlocks.current.clear()
    controlKeys.current.clear()
    submissionHint.current = null
    setSelectedSessionId(null)
    setSessionDetail(null)
    setSessionsPage(EMPTY_SESSIONS_PAGE)
    setDraft('')
    clearDraftAttachments()
    setSubmissionKey(null)
    submissionMessage.current = null
    setSearch('')
    setDebouncedSearch('')
    setActiveDialog(null)
    setDialogSessionId(null)
    setHistoryError(null)
    setConversationError(null)
    setSubmissionError(null)
    setRenameError(null)
    setRemovalError(null)
    setScopeError(null)
    setIsReadingHistory(false)
    setIsReadingMessages(false)
    setIsReadingOlderMessages(false)
  }, [cancelDictation, clearDraftAttachments])

  const readHistory = useCallback(
    async (nextSearch: string, cursor?: string, append = false) => {
      const generation = ++historyGeneration.current
      setIsReadingHistory(true)
      setHistoryError(null)
      try {
        const page = await readMentorSessions({
          search: nextSearch || undefined,
          cursor,
        })
        if (generation !== historyGeneration.current) return
        setSessionsPage((current) => ({
          items: append
            ? [
                ...current.items,
                ...page.items.filter(
                  (item) => !current.items.some((old) => old.id === item.id),
                ),
              ]
            : page.items,
          nextCursor: page.nextCursor,
        }))
        setScopeError(null)
      } catch (error) {
        if (generation !== historyGeneration.current) return
        setHistoryError('Não foi possível carregar o histórico. Tente novamente.')
        if (isMentorScopeError(error)) {
          clearPrivateState()
          setScopeError('Não foi possível confirmar sua sessão. Atualize a página.')
        }
      } finally {
        if (generation === historyGeneration.current) setIsReadingHistory(false)
      }
    },
    [clearPrivateState, readMentorSessions],
  )

  const readDetail = useCallback(
    async (sessionId: string, cursor?: string) => {
      const generation = ++detailGeneration.current
      setIsReadingMessages(true)
      setIsReadingOlderMessages(Boolean(cursor))
      setConversationError(null)
      try {
        const detail = await readMentorSession(sessionId, cursor)
        if (generation !== detailGeneration.current) return
        if (selectedSessionId !== sessionId && cursor) return
        setSessionDetail((current) =>
          mergeSessionDetail(current, detail, Boolean(cursor)),
        )
        setScopeError(null)
      } catch (error) {
        if (generation !== detailGeneration.current) return
        setConversationError('Não foi possível carregar a conversa. Tente novamente.')
        if (isMentorScopeError(error)) {
          clearPrivateState()
          setScopeError('Não foi possível confirmar sua sessão. Atualize a página.')
        }
      } finally {
        if (generation === detailGeneration.current) {
          setIsReadingMessages(false)
          setIsReadingOlderMessages(false)
        }
      }
    },
    [clearPrivateState, readMentorSession, selectedSessionId],
  )

  const refresh = useCallback(async () => {
    setIsValidatingScope(true)
    await Promise.all([
      readHistory(debouncedSearch),
      selectedSessionId ? readDetail(selectedSessionId) : Promise.resolve(),
    ])
    setIsValidatingScope(false)
  }, [debouncedSearch, readDetail, readHistory, selectedSessionId])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [search])

  useEffect(() => {
    void readHistory(debouncedSearch)
  }, [debouncedSearch, readHistory])

  useEffect(() => {
    clearPrivateState()
    setIsValidatingScope(true)
    void readHistory('').finally(() => setIsValidatingScope(false))
  }, [clearPrivateState, readHistory])

  useEffect(() => {
    function handleFocus() {
      void readHistory(debouncedSearch)
      if (selectedSessionId) void readDetail(selectedSessionId)
    }
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [debouncedSearch, readDetail, readHistory, selectedSessionId])

  const openPanel = useCallback(() => {
    setIsPanelOpen(true)
    void refresh()
  }, [refresh])
  const closePanel = useCallback(() => {
    cancelDictation()
    newBlocks.current.clear()
    setIsPanelOpen(false)
  }, [cancelDictation])
  const showPanelHistory = useCallback(() => setPanelView('history'), [])
  const showPanelConversation = useCallback(() => setPanelView('conversation'), [])
  const startNewConversation = useCallback(() => {
    cancelDictation()
    detailGeneration.current += 1
    setSelectedSessionId(null)
    setSessionDetail(null)
    setIsReadingMessages(false)
    setIsReadingOlderMessages(false)
    setConversationError(null)
    setDraft('')
    clearDraftAttachments()
    setSubmissionKey(null)
    submissionMessage.current = null
    setSubmissionError(null)
    resetCreateMentorSession()
    setPanelView('conversation')
  }, [cancelDictation, clearDraftAttachments, resetCreateMentorSession])
  const selectSession = useCallback(
    async (sessionId: string) => {
      cancelDictation()
      detailGeneration.current += 1
      setSelectedSessionId(sessionId)
      setSessionDetail(null)
      setDraft('')
      clearDraftAttachments()
      setSubmissionKey(null)
      submissionMessage.current = null
      setPanelView('conversation')
      await readDetail(sessionId)
    },
    [cancelDictation, clearDraftAttachments, readDetail],
  )
  const handleSetDraft = useCallback(
    (value: string) => {
      draftRevision.current += 1
      setDraft(value)
      if (!value.trim()) {
        setSubmissionKey(null)
        submissionMessage.current = null
      } else if (
        !submissionKey ||
        (submissionMessage.current !== null && submissionMessage.current !== value)
      ) {
        setSubmissionKey(crypto.randomUUID())
        submissionMessage.current = null
      }
    },
    [submissionKey],
  )
  async function addAttachments(files: File[]) {
    if (!files.length) return
    const currentCount = draftAttachmentsRef.current.length
    const additions = files.map((file, index) => {
      const mediaType = getMentorAttachmentMediaType(file.name)
      const isOverLimit = currentCount + index >= MAX_MENTOR_ATTACHMENTS
      const error = isOverLimit
        ? 'Você pode anexar até cinco arquivos por mensagem.'
        : !mediaType
          ? 'Formato não aceito. Use PNG, JPG, WebP, PDF, JSON, CSV ou TXT.'
          : file.size > MAX_MENTOR_ATTACHMENT_BYTES
            ? 'O arquivo excede o limite de 2 MB.'
            : file.size === 0
              ? 'O arquivo está vazio.'
              : null
      return {
        localKey: crypto.randomUUID(),
        uploadKey: crypto.randomUUID(),
        file,
        previewUrl:
          !error && mediaType?.startsWith('image/')
            ? createMentorAttachmentPreviewUrl(file)
            : null,
        attachment: null,
        error,
        retryable: false,
      } satisfies MentorDraftAttachment
    })
    updateDraftAttachments((current) => [...current, ...additions])
    setSubmissionKey(null)
    submissionMessage.current = null
    const validAdditions = additions.filter((attachment) => !attachment.error)
    if (!validAdditions.length) return

    const generation = attachmentGeneration.current
    await Promise.all(
      validAdditions.map((draftAttachment) =>
        uploadDraftAttachment(draftAttachment, generation),
      ),
    )
  }

  async function uploadDraftAttachment(
    draftAttachment: MentorDraftAttachment,
    generation: number,
  ) {
    if (
      generation !== attachmentGeneration.current ||
      !draftAttachmentsRef.current.some(
        (current) => current.localKey === draftAttachment.localKey,
      )
    )
      return

    let batchId = attachmentBatchIdRef.current
    let pendingBatch = attachmentBatchCreation.current
    try {
      if (!batchId) {
        if (!pendingBatch) {
          const creation = createMentorAttachmentBatch(selectedSessionId).then(
            (batch) => batch.batchId,
          )
          attachmentBatchCreation.current = creation
          pendingBatch = creation
        }
        batchId = await pendingBatch
        if (attachmentBatchCreation.current === pendingBatch)
          attachmentBatchCreation.current = null
        if (generation !== attachmentGeneration.current) return
        attachmentBatchIdRef.current = batchId
        setAttachmentBatchId(batchId)
      }
    } catch {
      if (pendingBatch && attachmentBatchCreation.current === pendingBatch)
        attachmentBatchCreation.current = null
      if (generation !== attachmentGeneration.current) return
      updateDraftAttachments((current) =>
        current.map((candidate) =>
          candidate.localKey === draftAttachment.localKey
            ? {
                ...candidate,
                error:
                  'Não foi possível preparar o envio. Tente novamente ou remova o arquivo.',
                retryable: true,
              }
            : candidate,
        ),
      )
      return
    }

    try {
      const attachment = await uploadMentorAttachment({
        batchId,
        uploadKey: draftAttachment.uploadKey,
        file: draftAttachment.file,
      })
      const isCurrent =
        generation === attachmentGeneration.current &&
        draftAttachmentsRef.current.some(
          (current) => current.localKey === draftAttachment.localKey,
        )
      if (!isCurrent) {
        try {
          await removeMentorAttachment({
            accountEmail,
            batchId,
            attachmentId: attachment.attachmentId,
          })
        } catch {
          // The server batch expiry remains the cleanup boundary for stale uploads.
        }
        return
      }
      updateDraftAttachments((current) =>
        current.map((candidate) =>
          candidate.localKey === draftAttachment.localKey
            ? {
                ...candidate,
                attachment,
                error:
                  attachment.status === 'failed'
                    ? getMentorAttachmentFailureMessage(attachment)
                    : null,
                retryable: false,
              }
            : candidate,
        ),
      )
    } catch (error) {
      if (generation !== attachmentGeneration.current) return
      updateDraftAttachments((current) =>
        current.map((candidate) =>
          candidate.localKey === draftAttachment.localKey
            ? {
                ...candidate,
                error: getMentorAttachmentRequestFailureMessage(error),
                retryable: true,
              }
            : candidate,
        ),
      )
    }
  }

  async function retryAttachment(localKey: string) {
    const draftAttachment = draftAttachmentsRef.current.find(
      (candidate) => candidate.localKey === localKey,
    )
    if (!draftAttachment?.retryable || draftAttachment.attachment) return
    const generation = attachmentGeneration.current
    const retrying = { ...draftAttachment, error: null, retryable: false }
    updateDraftAttachments((current) =>
      current.map((candidate) =>
        candidate.localKey === localKey ? retrying : candidate,
      ),
    )
    await uploadDraftAttachment(retrying, generation)
  }

  async function removeAttachment(localKey: string) {
    const draftAttachment = draftAttachmentsRef.current.find(
      (candidate) => candidate.localKey === localKey,
    )
    if (!draftAttachment) return
    const generation = attachmentGeneration.current
    const batchId = attachmentBatchIdRef.current
    if (draftAttachment.attachment && batchId) {
      try {
        await removeMentorAttachment({
          accountEmail,
          batchId,
          attachmentId: draftAttachment.attachment.attachmentId,
        })
      } catch {
        if (generation !== attachmentGeneration.current) return
        updateDraftAttachments((current) =>
          current.map((candidate) =>
            candidate.localKey === localKey
              ? {
                  ...candidate,
                  error: 'Não foi possível remover o arquivo. Tente novamente.',
                }
              : candidate,
          ),
        )
        return
      }
    }
    if (generation !== attachmentGeneration.current) return
    if (draftAttachment.previewUrl) URL.revokeObjectURL(draftAttachment.previewUrl)
    updateDraftAttachments((current) =>
      current.filter((candidate) => candidate.localKey !== localKey),
    )
    setSubmissionKey(null)
    submissionMessage.current = null
    if (draftAttachmentsRef.current.length === 0) {
      attachmentBatchIdRef.current = null
      setAttachmentBatchId(null)
    }
  }
  const handleSetSearch = useCallback(
    (value: string) => {
      if (value !== search) {
        historyGeneration.current += 1
        setSessionsPage(EMPTY_SESSIONS_PAGE)
        setIsReadingHistory(true)
        setHistoryError(null)
      }
      setSearch(value)
    },
    [search],
  )

  async function installDictationLanguage(surface: 'page' | 'fab' = 'page') {
    if (installationTarget.current) return
    const target = { surface }
    installationTarget.current = target
    await installLanguagePack()
    if (installationTarget.current === target) installationTarget.current = null
  }

  const isDictationBusy = ['preparing', 'recording', 'transcribing'].includes(
    dictationStatus,
  )
  const canStartDictation =
    dictationLanguageAvailability === 'available' &&
    !isDictationBusy &&
    !isValidatingScope &&
    !scopeError &&
    !isCreatingMentorSession &&
    !isSubmittingMessage &&
    !['queued', 'processing'].includes(sessionDetail?.response?.status ?? '') &&
    !sessionDetail?.pendingLearnerMessageId
  async function startDictation(surface: 'page' | 'fab' = 'page') {
    if (!canStartDictation || dictationTarget.current) return
    const target = {
      generation: detailGeneration.current,
      revision: draftRevision.current,
      surface,
    }
    const original = draft
    dictationTarget.current = target
    setDraftDictationError(null)
    const text = await startRecognition()
    if (dictationTarget.current !== target) return
    dictationTarget.current = null
    if (!text || target.generation !== detailGeneration.current) return
    if (target.revision !== draftRevision.current) {
      setDraftDictationError('Seu rascunho mudou. O ditado não foi aplicado.')
      return
    }
    handleSetDraft(original + (original ? '\n' : '') + text.trim())
  }

  const sendFirstMessage = useCallback(
    async (surface: 'page' | 'fab' = 'page') => {
      const readyAttachments = draftAttachmentsRef.current
      const canSendAttachments = readyAttachments.every(
        (draftAttachment) =>
          !draftAttachment.error &&
          draftAttachment.attachment &&
          ['ready', 'partial'].includes(draftAttachment.attachment.status),
      )
      if (
        dictationTarget.current ||
        submissionRunning.current ||
        (!draft.trim() && readyAttachments.length === 0) ||
        !canSendAttachments ||
        isCreatingMentorSession ||
        isSubmittingMessage ||
        sessionDetail?.pendingLearnerMessageId
      )
        return
      const content = draft.trim() ? draft : ''
      const generation = detailGeneration.current
      cancelDictation()
      submissionRunning.current = true
      const stableKey = submissionKey ?? crypto.randomUUID()
      const attachmentIds = readyAttachments.map(
        (draftAttachment) => draftAttachment.attachment?.attachmentId as string,
      )
      const attachmentInput =
        attachmentIds.length && attachmentBatchIdRef.current
          ? {
              attachmentBatchId: attachmentBatchIdRef.current,
              attachmentIds,
            }
          : {}
      if (!submissionKey) setSubmissionKey(stableKey)
      if (submissionMessage.current === null)
        submissionHint.current = surface === 'fab' ? contextHint : null
      submissionMessage.current = draft
      setSubmissionError(null)
      try {
        const detail = selectedSessionId
          ? await submitMentorMessage({
              sessionId: selectedSessionId,
              submissionKey: stableKey,
              content,
              contextHint: submissionHint.current,
              ...attachmentInput,
            })
          : await createMentorSession({
              submissionKey: stableKey,
              firstMessage: content,
              contextHint: submissionHint.current,
              ...attachmentInput,
            })
        if (generation !== detailGeneration.current) return
        setSelectedSessionId(detail.session.id)
        setSessionDetail(detail)
        setDraft('')
        clearDraftAttachments()
        setSubmissionKey(null)
        submissionMessage.current = null
        setPanelView('conversation')
        await readHistory(debouncedSearch)
      } catch (error) {
        if (generation !== detailGeneration.current) return
        if (isMentorScopeError(error)) {
          clearPrivateState()
          setScopeError('Não foi possível confirmar sua sessão. Atualize a página.')
        } else {
          setSubmissionError('Não foi possível enviar sua mensagem. Tente novamente.')
        }
      } finally {
        submissionRunning.current = false
      }
    },
    [
      cancelDictation,
      createMentorSession,
      clearPrivateState,
      clearDraftAttachments,
      debouncedSearch,
      draft,
      isCreatingMentorSession,
      readHistory,
      submissionKey,
      contextHint,
      selectedSessionId,
      sessionDetail?.pendingLearnerMessageId,
      submitMentorMessage,
      isSubmittingMessage,
    ],
  )

  const response = sessionDetail?.response ?? null
  const isResponseActive =
    response?.status === 'queued' || response?.status === 'processing'
  const isViewingConversation =
    (location.pathname === ROUTES.intelligence || isPanelOpen) &&
    panelView === 'conversation'
  const shouldAnimateBlock = useCallback((attemptId: string, blockKey: string) => {
    const key = `${attemptId}:${blockKey}`
    return newBlocks.current.has(key) && !presentedBlocks.current.has(key)
  }, [])
  const markBlockPresented = useCallback((attemptId: string, blockKey: string) => {
    presentedBlocks.current.add(`${attemptId}:${blockKey}`)
  }, [])
  function applyResponseEvent(event: MentorResponseEvent) {
    setSessionDetail((current) => {
      if (
        !current ||
        current.session.id !== event.sessionId ||
        current.response?.attemptId !== event.attemptId ||
        !['queued', 'processing'].includes(current.response.status) ||
        event.sequence <= current.response.lastSequence
      )
        return current
      const previous = current.response
      const shouldDiscardPartial = event.kind === 'cancelled' || event.kind === 'failed'
      const learnerAttachments = new Set(
        current.messages.items
          .filter(
            (message) =>
              message.id === previous.learnerMessageId &&
              message.sessionId === current.session.id &&
              message.role === 'learner',
          )
          .flatMap((message) =>
            (message.attachments ?? [])
              .filter((attachment) => ['ready', 'partial'].includes(attachment.status))
              .map((attachment) => attachment.attachmentId),
          ),
      )
      const safeEventBlock = event.block
        ? {
            ...event.block,
            sources: event.block.sources.filter((source) =>
              learnerAttachments.has(source.attachmentId),
            ),
          }
        : null
      const blocks = shouldDiscardPartial
        ? []
        : safeEventBlock &&
            !previous.blocks.some((block) => block.blockKey === safeEventBlock.blockKey)
          ? [...previous.blocks, safeEventBlock].sort(
              (left, right) => left.ordinal - right.ordinal,
            )
          : previous.blocks
      if (shouldDiscardPartial) newBlocks.current.clear()
      else if (
        safeEventBlock &&
        isViewingConversation &&
        document.visibilityState === 'visible'
      )
        newBlocks.current.add(`${event.attemptId}:${safeEventBlock.blockKey}`)
      const consultations = shouldDiscardPartial
        ? []
        : event.consultation && !previous.consultations.includes(event.consultation)
          ? [...previous.consultations, event.consultation]
          : previous.consultations
      return {
        ...current,
        response: {
          ...previous,
          blocks,
          consultations,
          status: event.status,
          progress: ['queued', 'processing'].includes(event.status)
            ? (event.progress ?? previous.progress ?? null)
            : null,
          lastSequence: event.sequence,
          failureCode: event.failureCode,
        },
        pendingLearnerMessageId:
          event.status === 'completed' ? null : current.pendingLearnerMessageId,
      }
    })
    if (event.kind === 'completed' && selectedSessionId)
      void readDetail(selectedSessionId)
  }
  async function reconcileResponse() {
    if (!selectedSessionId) return null
    const generation = detailGeneration.current
    const attemptId = response?.attemptId
    let detail: MentorSessionDetail
    try {
      detail = await readMentorSession(selectedSessionId)
    } catch (error) {
      if (generation === detailGeneration.current && isMentorScopeError(error)) {
        clearPrivateState()
        setScopeError('Não foi possível confirmar sua sessão. Atualize a página.')
      }
      throw error
    }
    if (generation !== detailGeneration.current) return null
    setSessionDetail((current) =>
      current?.response?.attemptId !== attemptId
        ? current
        : mergeSessionDetail(current, detail),
    )
    return detail.response ?? null
  }
  useMentorResponseStream({
    sessionId: selectedSessionId,
    attemptId: response?.attemptId ?? null,
    afterSequence: response?.lastSequence ?? 0,
    enabled: Boolean(isResponseActive && !scopeError),
    openEventSource: NativeMentorEventSource,
    onEvent: applyResponseEvent,
    reconcile: reconcileResponse,
    onUnavailable: () =>
      setConversationError(
        'Não foi possível acompanhar a resposta. Atualize a conversa.',
      ),
  })
  async function changeResponse(action: 'cancel' | 'retry') {
    if (!selectedSessionId || !response || isCancellingResponse || isRetryingResponse)
      return
    const sessionId = selectedSessionId
    const attemptId = response.attemptId
    const generation = detailGeneration.current
    const key = `${attemptId}:${action}`
    const submissionKey = controlKeys.current.get(key) ?? crypto.randomUUID()
    controlKeys.current.set(key, submissionKey)
    try {
      const snapshot = await (action === 'cancel'
        ? cancelMentorResponse
        : retryMentorResponse)({ sessionId, attemptId, submissionKey })
      if (generation !== detailGeneration.current) return
      setSessionDetail((current) => {
        if (
          current?.session.id !== sessionId ||
          current.response?.attemptId !== attemptId
        )
          return current
        const nextResponse = chooseResponseSnapshot(current.response, snapshot)
        if (nextResponse === current.response) return current
        newBlocks.current.clear()
        return { ...current, response: nextResponse }
      })
      setSubmissionError(null)
    } catch (error) {
      if (generation !== detailGeneration.current) return
      if (isMentorScopeError(error)) {
        clearPrivateState()
        setScopeError('Não foi possível confirmar sua sessão. Atualize a página.')
      } else setSubmissionError('Não foi possível alterar a resposta. Tente novamente.')
    }
  }
  function cancelResponse() {
    return changeResponse('cancel')
  }
  function retryResponse() {
    return changeResponse('retry')
  }
  async function submitMessage(input: SubmitMentorMessageInput) {
    if (
      !selectedSessionId ||
      isSubmittingMessage ||
      sessionDetail?.pendingLearnerMessageId
    )
      return
    const generation = detailGeneration.current
    try {
      const detail = await submitMentorMessage({ ...input, sessionId: selectedSessionId })
      if (generation === detailGeneration.current) setSessionDetail(detail)
    } catch (error) {
      if (isMentorScopeError(error)) clearPrivateState()
      else setSubmissionError('Não foi possível enviar sua mensagem. Tente novamente.')
    }
  }

  const loadMoreSessions = useCallback(async () => {
    if (!sessionsPage.nextCursor || isReadingHistory) return
    await readHistory(debouncedSearch, sessionsPage.nextCursor, true)
  }, [debouncedSearch, isReadingHistory, readHistory, sessionsPage.nextCursor])

  const loadOlderMessages = useCallback(async () => {
    if (!selectedSessionId || !sessionDetail?.messages.nextCursor || isReadingMessages)
      return
    await readDetail(selectedSessionId, sessionDetail.messages.nextCursor)
  }, [isReadingMessages, readDetail, selectedSessionId, sessionDetail])

  const openRenameDialog = useCallback((sessionId: string) => {
    setDialogSessionId(sessionId)
    setActiveDialog('rename')
    setRenameError(null)
  }, [])
  const openRemoveDialog = useCallback((sessionId: string) => {
    setDialogSessionId(sessionId)
    setActiveDialog('remove')
    setRemovalError(null)
  }, [])
  const closeDialog = useCallback(() => {
    setActiveDialog(null)
    setDialogSessionId(null)
    setRenameError(null)
    setRemovalError(null)
    resetRenameMentorSession()
    resetRemoveMentorSession()
  }, [resetRemoveMentorSession, resetRenameMentorSession])

  const renameSession = useCallback(
    async (title: string) => {
      if (!dialogSessionId || isRenamingMentorSession) return
      setRenameError(null)
      try {
        const renamed = await renameMentorSession({ sessionId: dialogSessionId, title })
        setSessionsPage((current) => ({
          ...current,
          items: current.items.map((item) =>
            item.id === renamed.id ? { ...item, title: renamed.title } : item,
          ),
        }))
        setSessionDetail((current) =>
          current?.session.id === renamed.id ? { ...current, session: renamed } : current,
        )
        await readHistory(debouncedSearch)
        closeDialog()
      } catch (error) {
        if (isMentorScopeError(error)) {
          clearPrivateState()
          setScopeError('Não foi possível confirmar sua sessão. Atualize a página.')
        } else {
          setRenameError('Não foi possível renomear a conversa. Tente novamente.')
        }
      }
    },
    [
      closeDialog,
      clearPrivateState,
      debouncedSearch,
      dialogSessionId,
      isRenamingMentorSession,
      readHistory,
      renameMentorSession,
    ],
  )

  const removeSession = useCallback(async () => {
    if (!dialogSessionId || isRemovingMentorSession) return
    setRemovalError(null)
    try {
      await removeMentorSession(dialogSessionId)
      setSessionsPage((current) => ({
        ...current,
        items: current.items.filter((item) => item.id !== dialogSessionId),
      }))
      if (selectedSessionId === dialogSessionId) {
        cancelDictation()
        detailGeneration.current += 1
        setSelectedSessionId(null)
        setSessionDetail(null)
        setPanelView('conversation')
        setIsReadingMessages(false)
        setIsReadingOlderMessages(false)
        setConversationError(null)
        setDraft('')
        clearDraftAttachments()
        setSubmissionKey(null)
        submissionMessage.current = null
        if (
          location.pathname === ROUTES.intelligence &&
          location.search.session === dialogSessionId
        ) {
          void navigate({
            to: ROUTES.intelligence,
            search: { session: undefined },
            replace: true,
          })
        }
      }
      await readHistory(debouncedSearch)
      closeDialog()
    } catch (error) {
      if (isMentorScopeError(error)) {
        clearPrivateState()
        setScopeError('Não foi possível confirmar sua sessão. Atualize a página.')
      } else {
        setRemovalError('Não foi possível excluir a conversa. Tente novamente.')
      }
    }
  }, [
    cancelDictation,
    closeDialog,
    clearPrivateState,
    clearDraftAttachments,
    debouncedSearch,
    dialogSessionId,
    isRemovingMentorSession,
    location.pathname,
    location.search,
    navigate,
    readHistory,
    removeMentorSession,
    selectedSessionId,
  ])

  const expandConversation = useCallback(async () => {
    cancelDictation()
    setIsPanelOpen(false)
    await refresh()
    await navigate({
      to: ROUTES.intelligence,
      search: { session: selectedSessionId ?? undefined },
    })
  }, [cancelDictation, navigate, refresh, selectedSessionId])

  return {
    dictationStatus: draftDictationError ? 'error' : dictationStatus,
    dictationElapsedSeconds,
    dictationLanguageAvailability,
    dictationInstallationStatus,
    dictationInstallationError,
    dictationError: draftDictationError ?? recognitionError,
    isDictationBusy,
    canStartDictation,
    canInstallDictationLanguage,
    startDictation,
    finishDictation: finishRecognition,
    cancelDictation,
    installDictationLanguage,
    releaseDictationSurface,
    response,
    isCancellingResponse,
    isRetryingResponse,
    submitMessage,
    cancelResponse,
    retryResponse,
    shouldAnimateBlock,
    markBlockPresented,
    selectedSessionId,
    sessionDetail,
    sessionsPage,
    draft,
    draftAttachments,
    isPreparingAttachments,
    search,
    isPanelOpen,
    panelView,
    activeDialog,
    dialogSessionId,
    isValidatingScope,
    isReadingHistory,
    isReadingMessages,
    isReadingOlderMessages,
    isSubmittingFirstMessage: isCreatingMentorSession || isSubmittingMessage,
    isRenamingSession: isRenamingMentorSession,
    isRemovingSession: isRemovingMentorSession,
    scopeError,
    historyError,
    conversationError,
    submissionError,
    renameError,
    removalError,
    openPanel,
    closePanel,
    showPanelHistory,
    showPanelConversation,
    expandConversation,
    startNewConversation,
    selectSession,
    setDraft: handleSetDraft,
    addAttachments,
    retryAttachment,
    removeAttachment,
    setSearch: handleSetSearch,
    sendFirstMessage,
    loadMoreSessions,
    loadOlderMessages,
    openRenameDialog,
    openRemoveDialog,
    closeDialog,
    renameSession,
    removeSession,
    refresh,
  }
}

function isMentorScopeError(error: unknown): boolean {
  return (
    error instanceof Error && /sessão expirou|sessão da conta mudou/i.test(error.message)
  )
}

function getMentorAttachmentMediaType(filename: string): string | null {
  const extension = filename.split('.').at(-1)?.toLowerCase()
  switch (extension) {
    case 'png':
      return 'image/png'
    case 'jpg':
    case 'jpeg':
      return 'image/jpeg'
    case 'webp':
      return 'image/webp'
    case 'pdf':
      return 'application/pdf'
    case 'json':
      return 'application/json'
    case 'csv':
      return 'text/csv'
    case 'txt':
      return 'text/plain'
    default:
      return null
  }
}

function createMentorAttachmentPreviewUrl(file: File): string | null {
  try {
    return URL.createObjectURL(file)
  } catch {
    return null
  }
}

function getMentorAttachmentFailureMessage(_attachment: MentorAttachment): string {
  return 'Não foi possível interpretar este arquivo. Remova-o ou tente outro arquivo.'
}

function isTerminalMentorAttachmentStatus(status: MentorAttachment['status']): boolean {
  return ['ready', 'partial', 'failed', 'removed'].includes(status)
}

function getMentorAttachmentStatusRank(status: MentorAttachment['status']): number {
  return {
    uploading: 0,
    processing: 1,
    ready: 2,
    partial: 2,
    failed: 2,
    removed: 3,
  }[status]
}

function getMentorAttachmentRequestFailureMessage(_error: unknown): string {
  return 'Não foi possível enviar o arquivo. Tente novamente ou remova-o.'
}

function chooseResponseSnapshot(
  current: MentorResponseSnapshot | null | undefined,
  incoming: MentorResponseSnapshot | null | undefined,
): MentorResponseSnapshot | null {
  if (!current) return incoming ?? null
  if (!incoming || incoming.lastSequence <= current.lastSequence) return current
  if (incoming.attemptId !== current.attemptId) return incoming
  if (!['queued', 'processing'].includes(current.status)) return current
  if (incoming.status === 'cancelled') return incoming
  const blockKeys = new Set(incoming.blocks.map((block) => block.blockKey))
  return {
    ...incoming,
    blocks: [
      ...current.blocks.filter((block) => !blockKeys.has(block.blockKey)),
      ...incoming.blocks,
    ].sort((left, right) => left.ordinal - right.ordinal),
    consultations: [...new Set([...current.consultations, ...incoming.consultations])],
  }
}
function mergeSessionDetail(
  current: MentorSessionDetail | null,
  incoming: MentorSessionDetail,
  isOlderPage = false,
): MentorSessionDetail {
  if (!current || current.session.id !== incoming.session.id) return incoming
  const response = chooseResponseSnapshot(current.response, incoming.response)
  const pageIds = new Set(incoming.messages.items.map((message) => message.id))
  const messages = [
    ...current.messages.items.filter((message) => !pageIds.has(message.id)),
    ...incoming.messages.items,
  ].sort((left, right) => left.createdAt.localeCompare(right.createdAt))
  const nextCursor =
    isOlderPage || current.messages.items.length <= incoming.messages.items.length
      ? incoming.messages.nextCursor
      : current.messages.nextCursor
  return {
    ...incoming,
    response,
    pendingLearnerMessageId:
      response?.status === 'completed' ? null : incoming.pendingLearnerMessageId,
    messages: { items: messages, nextCursor },
  }
}
