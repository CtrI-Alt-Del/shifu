import { useLocation, useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useRef, useState } from 'react'

import type {
  MentorSessionDetail,
  MentorSessionsPage,
} from '@/rest/services/intelligence-service'
import { ROUTES } from '@/constants/routes'
import { useCreateMentorSessionAction } from '@/ui/intelligence/hooks/use-create-mentor-session-action'
import { useMentorSessionQuery } from '@/ui/intelligence/hooks/use-mentor-session-query'
import { useMentorSessionsQuery } from '@/ui/intelligence/hooks/use-mentor-sessions-query'
import { useRemoveMentorSessionAction } from '@/ui/intelligence/hooks/use-remove-mentor-session-action'
import { useRenameMentorSessionAction } from '@/ui/intelligence/hooks/use-rename-mentor-session-action'

import type { MentorContextValue } from './types'

const SEARCH_DEBOUNCE_MS = 300
const EMPTY_SESSIONS_PAGE: MentorSessionsPage = { items: [], nextCursor: null }

export function useMentorContextProvider(accountEmail: string): MentorContextValue {
  const navigate = useNavigate()
  const location = useLocation()
  const { readMentorSessions } = useMentorSessionsQuery(accountEmail)
  const { readMentorSession } = useMentorSessionQuery(accountEmail)
  const { createMentorSession, isCreatingMentorSession, resetCreateMentorSession } =
    useCreateMentorSessionAction(accountEmail)
  const { isRenamingMentorSession, renameMentorSession, resetRenameMentorSession } =
    useRenameMentorSessionAction(accountEmail)
  const { isRemovingMentorSession, removeMentorSession, resetRemoveMentorSession } =
    useRemoveMentorSessionAction(accountEmail)

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [sessionDetail, setSessionDetail] = useState<MentorSessionDetail | null>(null)
  const [sessionsPage, setSessionsPage] = useState(EMPTY_SESSIONS_PAGE)
  const [draft, setDraft] = useState('')
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
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [conversationError, setConversationError] = useState<string | null>(null)
  const [submissionError, setSubmissionError] = useState<string | null>(null)
  const [renameError, setRenameError] = useState<string | null>(null)
  const [removalError, setRemovalError] = useState<string | null>(null)
  const [scopeError, setScopeError] = useState<string | null>(null)
  const historyGeneration = useRef(0)
  const detailGeneration = useRef(0)
  const submissionMessage = useRef<string | null>(null)

  const clearPrivateState = useCallback(() => {
    historyGeneration.current += 1
    detailGeneration.current += 1
    setSelectedSessionId(null)
    setSessionDetail(null)
    setSessionsPage(EMPTY_SESSIONS_PAGE)
    setDraft('')
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
  }, [])

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
      setConversationError(null)
      try {
        const detail = await readMentorSession(sessionId, cursor)
        if (generation !== detailGeneration.current) return
        if (selectedSessionId !== sessionId && cursor) return
        setSessionDetail((current) => {
          if (!cursor || !current || current.session.id !== sessionId) return detail
          const pageIds = new Set(detail.messages.items.map((message) => message.id))
          const messages = [
            ...current.messages.items.filter((message) => !pageIds.has(message.id)),
            ...detail.messages.items,
          ].sort((left, right) => left.createdAt.localeCompare(right.createdAt))
          return {
            ...detail,
            messages: { items: messages, nextCursor: detail.messages.nextCursor },
          }
        })
        setScopeError(null)
      } catch (error) {
        if (generation !== detailGeneration.current) return
        setConversationError('Não foi possível carregar a conversa. Tente novamente.')
        if (isMentorScopeError(error)) {
          clearPrivateState()
          setScopeError('Não foi possível confirmar sua sessão. Atualize a página.')
        }
      } finally {
        if (generation === detailGeneration.current) setIsReadingMessages(false)
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
    const handleFocus = () => {
      setIsValidatingScope(true)
      void refresh().finally(() => {
        setIsValidatingScope(false)
      })
    }
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [refresh])

  const openPanel = useCallback(() => {
    setIsPanelOpen(true)
    void refresh()
  }, [refresh])
  const closePanel = useCallback(() => setIsPanelOpen(false), [])
  const showPanelHistory = useCallback(() => setPanelView('history'), [])
  const showPanelConversation = useCallback(() => setPanelView('conversation'), [])
  const startNewConversation = useCallback(() => {
    detailGeneration.current += 1
    setSelectedSessionId(null)
    setSessionDetail(null)
    setIsReadingMessages(false)
    setConversationError(null)
    setDraft('')
    setSubmissionKey(null)
    submissionMessage.current = null
    setSubmissionError(null)
    resetCreateMentorSession()
    setPanelView('conversation')
  }, [resetCreateMentorSession])
  const selectSession = useCallback(
    async (sessionId: string) => {
      detailGeneration.current += 1
      setSelectedSessionId(sessionId)
      setSessionDetail(null)
      setDraft('')
      setSubmissionKey(null)
      submissionMessage.current = null
      setPanelView('conversation')
      await readDetail(sessionId)
    },
    [readDetail],
  )
  const handleSetDraft = useCallback(
    (value: string) => {
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

  const sendFirstMessage = useCallback(async () => {
    if (!draft.trim() || isCreatingMentorSession) return
    const stableKey = submissionKey ?? crypto.randomUUID()
    if (!submissionKey) setSubmissionKey(stableKey)
    submissionMessage.current = draft
    setSubmissionError(null)
    try {
      const detail = await createMentorSession({
        submissionKey: stableKey,
        firstMessage: draft,
      })
      setSelectedSessionId(detail.session.id)
      setSessionDetail(detail)
      setDraft('')
      setSubmissionKey(null)
      submissionMessage.current = null
      setPanelView('conversation')
      await readHistory(debouncedSearch)
    } catch (error) {
      if (isMentorScopeError(error)) {
        clearPrivateState()
        setScopeError('Não foi possível confirmar sua sessão. Atualize a página.')
      } else {
        setSubmissionError('Não foi possível enviar sua mensagem. Tente novamente.')
      }
    }
  }, [
    createMentorSession,
    clearPrivateState,
    debouncedSearch,
    draft,
    isCreatingMentorSession,
    readHistory,
    submissionKey,
  ])

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
        detailGeneration.current += 1
        setSelectedSessionId(null)
        setSessionDetail(null)
        setPanelView('conversation')
        setIsReadingMessages(false)
        setConversationError(null)
        setDraft('')
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
    closeDialog,
    clearPrivateState,
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
    setIsPanelOpen(false)
    await refresh()
    await navigate({
      to: ROUTES.intelligence,
      search: { session: selectedSessionId ?? undefined },
    })
  }, [navigate, refresh, selectedSessionId])

  return {
    selectedSessionId,
    sessionDetail,
    sessionsPage,
    draft,
    search,
    isPanelOpen,
    panelView,
    activeDialog,
    dialogSessionId,
    isValidatingScope,
    isReadingHistory,
    isReadingMessages,
    isSubmittingFirstMessage: isCreatingMentorSession,
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
