import { useEffect, useRef, useState } from 'react'

import { buildPracticePhotoPath } from '@/constants/routes'
import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import type {
  PracticalPreparationQuestion as PracticalPreparationQuestionData,
  PracticalPreparationRecord,
} from '@/core/learning/choice-activity'
import {
  type PracticePhotoFileProblem,
  inspectPracticePhotoFile,
} from '@/core/learning/practice-photo-rules'

import {
  type PracticeDraftErrorKind,
  PracticeDraftRequestError,
} from './practice-draft-request-error'
import type { PracticeDraftIds } from './practice-draft-server-functions'
import { usePracticeDraftQuery } from './use-practice-draft-query'
import { useRemovePracticePhotoAction } from './use-remove-practice-photo-action'
import { useSavePracticeReflectionAction } from './use-save-practice-reflection-action'
import { useUploadPracticePhotoAction } from './use-upload-practice-photo-action'

const REFLECTION_AUTOSAVE_DELAY_MS = 800
const MEDIA_TYPE_LABELS: Record<string, string> = {
  'image/jpeg': 'JPEG',
  'image/png': 'PNG',
  'image/webp': 'WebP',
}
const SIZE_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })

export type PracticalPreparationDraftState = {
  revision: number | null
  reflection: string
  isComplete: boolean
  hasUnsavedChanges: boolean
}

export type PracticalPreparationQuestionProps = {
  question: PracticalPreparationQuestionData
  activityTitle?: string
  difficulty?: ActivityDifficulty
  questionNumber: number
  totalQuestions: number
  ids: PracticeDraftIds | null
  isOnlineAuthority: boolean
  disabled?: boolean
  conflictCount?: number
  onDraftStateChange: (state: PracticalPreparationDraftState) => void
  onSessionExpired?: () => void
}

export type PracticeRecordStatus =
  | 'missing'
  | 'uploading'
  | 'removing'
  | 'ready'
  | 'failed'

export type PracticeRecordView = {
  record: PracticalPreparationRecord
  status: PracticeRecordStatus
  thumbnailUrl: string | null
  fileName: string | null
  meta: string | null
  message: string | null
  canRetry: boolean
}

export type PracticeViewState = 'unavailable' | 'offline' | 'loading' | 'error' | 'ready'
export type PracticeSaveState = 'saved' | 'saving' | 'failed'

type PhotoTransfer = {
  status: 'uploading' | 'removing' | 'failed'
  fileName: string | null
  message: string | null
  canRetry: boolean
}

type ReflectionSaveState = 'saved' | 'pending' | 'saving' | 'failed'

const FILE_PROBLEM_MESSAGES: Record<PracticePhotoFileProblem, string> = {
  empty: 'O arquivo está vazio. Escolha outra foto.',
  'too-large': 'A foto excede 10 MB. Escolha uma foto menor.',
  unsupported: 'Este arquivo não é uma foto JPEG, PNG ou WebP.',
}

const UPLOAD_FAILURE_MESSAGES: Record<PracticeDraftErrorKind, string> = {
  'invalid-request': 'Não foi possível enviar a foto. Escolha a foto novamente.',
  unauthorized: 'Sua sessão expirou. Entre novamente para continuar.',
  'not-found': 'Esta Atividade não está mais disponível.',
  'draft-closed': 'Este rascunho foi encerrado. Recarregue a página.',
  'too-large': 'A foto excede 10 MB. Escolha uma foto menor.',
  unsupported: 'Este arquivo não é uma foto JPEG, PNG ou WebP válida.',
  'upload-key-conflict': 'Não foi possível reutilizar este envio. Tente novamente.',
  'evaluation-pending': 'Há uma avaliação pendente nesta Habilidade.',
  unavailable: 'Não foi possível enviar a foto. Tente novamente.',
}

const REMOVE_FAILURE_MESSAGE = 'Não foi possível remover a foto. Tente novamente.'

const LOAD_FAILURE_MESSAGES: Record<PracticeDraftErrorKind, string> = {
  'invalid-request': 'Não foi possível carregar seu rascunho.',
  unauthorized: 'Sua sessão expirou. Entre novamente para continuar.',
  'not-found': 'Esta Atividade não está mais disponível.',
  'draft-closed': 'Este rascunho foi encerrado. Recarregue a página.',
  'too-large': 'Não foi possível carregar seu rascunho.',
  unsupported: 'Não foi possível carregar seu rascunho.',
  'upload-key-conflict': 'Não foi possível carregar seu rascunho.',
  'evaluation-pending': 'Há uma avaliação pendente nesta Habilidade.',
  unavailable: 'Não foi possível carregar seu rascunho agora.',
}

export function usePracticalPreparationQuestion({
  conflictCount = 0,
  disabled = false,
  ids,
  isOnlineAuthority,
  onDraftStateChange,
  onSessionExpired,
  question,
}: PracticalPreparationQuestionProps) {
  const { practiceDraft, practiceDraftError, reloadPracticeDraft } =
    usePracticeDraftQuery({ ids, isEnabled: isOnlineAuthority })
  const { savePracticeReflection } = useSavePracticeReflectionAction(ids)
  const { uploadPracticePhoto } = useUploadPracticePhotoAction(ids)
  const { removePracticePhoto } = useRemovePracticePhotoAction(ids)
  const [reflection, setReflection] = useState('')
  const [isReflectionOpen, setIsReflectionOpen] = useState(false)
  const [reflectionSaveState, setReflectionSaveState] =
    useState<ReflectionSaveState>('saved')
  const [transfers, setTransfers] = useState<Record<string, PhotoTransfer>>({})
  const [notice, setNotice] = useState<'conflict' | null>(null)
  const hasHydratedRef = useRef(false)
  const latestReflectionRef = useRef('')
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isSavingRef = useRef(false)
  const needsSaveRef = useRef(false)
  const pendingUploadsRef = useRef<Record<string, { file: File; uploadKey: string }>>({})
  const handledConflictCountRef = useRef(0)

  useEffect(() => {
    if (!practiceDraft || hasHydratedRef.current) return
    hasHydratedRef.current = true
    latestReflectionRef.current = practiceDraft.reflection
    setReflection(practiceDraft.reflection)
    if (practiceDraft.reflection) setIsReflectionOpen(true)
  }, [practiceDraft])

  useEffect(() => {
    if (conflictCount === 0 || handledConflictCountRef.current === conflictCount) return
    handledConflictCountRef.current = conflictCount
    void reloadPracticeDraft().then((result) => {
      if (!result.data) return
      clearTimerRef(autosaveTimerRef)
      latestReflectionRef.current = result.data.reflection
      setReflection(result.data.reflection)
      setReflectionSaveState('saved')
      setIsReflectionOpen(Boolean(result.data.reflection))
      setTransfers({})
      pendingUploadsRef.current = {}
      setNotice('conflict')
    })
  }, [conflictCount, reloadPracticeDraft])

  useEffect(() => () => clearTimerRef(autosaveTimerRef), [])

  const records: readonly PracticeRecordView[] = question.records.map((record) => {
    const photo = practiceDraft?.photos.find(({ recordKey }) => recordKey === record.key)
    const transfer = transfers[record.key]
    const status: PracticeRecordStatus =
      transfer?.status === 'uploading' || transfer?.status === 'removing'
        ? transfer.status
        : photo
          ? photo.state === 'ready'
            ? 'ready'
            : photo.state === 'uploading'
              ? 'uploading'
              : 'failed'
          : transfer?.status === 'failed'
            ? 'failed'
            : 'missing'
    return {
      record,
      status,
      thumbnailUrl:
        ids && photo?.state === 'ready'
          ? `${buildPracticePhotoPath({ ...ids, recordKey: record.key })}?v=${encodeURIComponent(photo.photoId)}`
          : null,
      fileName: transfer?.fileName ?? null,
      meta:
        photo?.state === 'ready'
          ? `${MEDIA_TYPE_LABELS[photo.mediaType] ?? 'Imagem'} · ${formatPhotoSize(photo.sizeBytes)}`
          : null,
      message:
        transfer?.status === 'failed'
          ? transfer.message
          : photo?.state === 'failed'
            ? 'O envio desta foto falhou. Escolha a foto novamente.'
            : null,
      canRetry: transfer?.status === 'failed' && transfer.canRetry,
    }
  })

  const viewState: PracticeViewState = practiceDraft
    ? 'ready'
    : !ids
      ? 'unavailable'
      : !isOnlineAuthority
        ? 'offline'
        : practiceDraftError
          ? 'error'
          : 'loading'
  const isOffline = Boolean(practiceDraft) && !isOnlineAuthority
  const loadErrorMessage = practiceDraftError
    ? LOAD_FAILURE_MESSAGES[practiceDraftError.kind]
    : null
  const isTransferring = records.some(
    ({ status }) => status === 'uploading' || status === 'removing',
  )
  const saveState: PracticeSaveState =
    reflectionSaveState === 'failed'
      ? 'failed'
      : reflectionSaveState === 'saved' && !isTransferring
        ? 'saved'
        : 'saving'
  const saveStateLabel =
    saveState === 'saved'
      ? 'Rascunho salvo na sua conta'
      : saveState === 'saving'
        ? 'Salvando rascunho…'
        : 'Rascunho não salvo'
  const saveStateDetail =
    saveState === 'failed'
      ? 'Tente novamente antes de sair. As últimas alterações ainda não estão salvas na sua conta.'
      : isOffline
        ? 'Sem conexão. As alterações só serão salvas quando a conexão voltar.'
        : null
  const saveStateHelper =
    saveState === 'failed'
      ? null
      : isOffline
        ? null
        : saveState === 'saving'
          ? isTransferring
            ? 'Você pode continuar enquanto a foto é adicionada.'
            : 'Você pode continuar enquanto salvamos.'
          : 'Continue de onde parou, inclusive em outro dispositivo.'
  const isControlsDisabled = disabled || !isOnlineAuthority
  const isComplete =
    viewState === 'ready' && records.every(({ status }) => status === 'ready')
  const hasUnsavedChanges = reflectionSaveState !== 'saved'
  const revision = practiceDraft?.revision ?? null

  // The page callback changes identity on every render, so the effect reads it
  // through a ref and only reacts to the draft values themselves.
  const onDraftStateChangeRef = useRef(onDraftStateChange)
  onDraftStateChangeRef.current = onDraftStateChange
  useEffect(() => {
    onDraftStateChangeRef.current({ revision, reflection, isComplete, hasUnsavedChanges })
  }, [revision, reflection, isComplete, hasUnsavedChanges])

  useEffect(() => {
    if (practiceDraftError?.kind === 'unauthorized') onSessionExpired?.()
  }, [practiceDraftError, onSessionExpired])

  function updateTransfer(recordKey: string, transfer: PhotoTransfer | null) {
    setTransfers((current) => {
      const next = { ...current }
      if (transfer) next[recordKey] = transfer
      else delete next[recordKey]
      return next
    })
  }

  async function persistReflection() {
    if (isSavingRef.current) {
      needsSaveRef.current = true
      return
    }
    isSavingRef.current = true
    const value = latestReflectionRef.current
    setReflectionSaveState('saving')
    try {
      await savePracticeReflection(value)
      if (latestReflectionRef.current === value && autosaveTimerRef.current === null)
        setReflectionSaveState('saved')
    } catch (error) {
      if (error instanceof PracticeDraftRequestError && error.kind === 'unauthorized')
        onSessionExpired?.()
      setReflectionSaveState('failed')
    } finally {
      isSavingRef.current = false
      if (needsSaveRef.current) {
        needsSaveRef.current = false
        void persistReflection()
      }
    }
  }

  function handleToggleReflection() {
    setIsReflectionOpen((current) => !current)
  }

  function handleChangeReflection(value: string) {
    if (isControlsDisabled) return
    setReflection(value)
    latestReflectionRef.current = value
    setReflectionSaveState('pending')
    setNotice(null)
    clearTimerRef(autosaveTimerRef)
    autosaveTimerRef.current = setTimeout(() => {
      autosaveTimerRef.current = null
      void persistReflection()
    }, REFLECTION_AUTOSAVE_DELAY_MS)
  }

  function handleBlurReflection() {
    if (autosaveTimerRef.current === null) return
    clearTimerRef(autosaveTimerRef)
    void persistReflection()
  }

  function handleRetrySaveReflection() {
    clearTimerRef(autosaveTimerRef)
    void persistReflection()
  }

  async function startUpload(recordKey: string) {
    const pending = pendingUploadsRef.current[recordKey]
    if (!pending) return
    updateTransfer(recordKey, {
      status: 'uploading',
      fileName: pending.file.name,
      message: null,
      canRetry: false,
    })
    try {
      await uploadPracticePhoto({
        recordKey,
        file: pending.file,
        uploadKey: pending.uploadKey,
      })
      delete pendingUploadsRef.current[recordKey]
      updateTransfer(recordKey, null)
    } catch (error) {
      const kind: PracticeDraftErrorKind =
        error instanceof PracticeDraftRequestError ? error.kind : 'unavailable'
      if (kind === 'unauthorized') onSessionExpired?.()
      // A reused upload key with different content needs a fresh key to retry.
      if (kind === 'upload-key-conflict')
        pending.uploadKey = globalThis.crypto.randomUUID()
      const canRetry = kind === 'unavailable' || kind === 'upload-key-conflict'
      if (!canRetry) delete pendingUploadsRef.current[recordKey]
      updateTransfer(recordKey, {
        status: 'failed',
        fileName: pending.file.name,
        message: UPLOAD_FAILURE_MESSAGES[kind],
        canRetry,
      })
    }
  }

  async function handleSelectPhoto(recordKey: string, file: File) {
    if (isControlsDisabled) return
    setNotice(null)
    const problem = inspectPracticePhotoFile(file)
    if (problem) {
      delete pendingUploadsRef.current[recordKey]
      updateTransfer(recordKey, {
        status: 'failed',
        fileName: file.name,
        message: FILE_PROBLEM_MESSAGES[problem],
        canRetry: false,
      })
      return
    }
    // The same upload key is reused when this file is retried, so a repeated
    // request never duplicates the photo on the server.
    pendingUploadsRef.current[recordKey] = {
      file,
      uploadKey: globalThis.crypto.randomUUID(),
    }
    await startUpload(recordKey)
  }

  async function handleRetryPhoto(recordKey: string) {
    if (isControlsDisabled) return
    await startUpload(recordKey)
  }

  async function handleRemovePhoto(recordKey: string) {
    if (isControlsDisabled) return
    setNotice(null)
    delete pendingUploadsRef.current[recordKey]
    updateTransfer(recordKey, {
      status: 'removing',
      fileName: null,
      message: null,
      canRetry: false,
    })
    try {
      await removePracticePhoto(recordKey)
      updateTransfer(recordKey, null)
    } catch (error) {
      if (error instanceof PracticeDraftRequestError && error.kind === 'unauthorized')
        onSessionExpired?.()
      updateTransfer(recordKey, {
        status: 'failed',
        fileName: null,
        message: REMOVE_FAILURE_MESSAGE,
        canRetry: false,
      })
    }
  }

  async function handleReloadDraft() {
    await reloadPracticeDraft()
  }

  return {
    viewState,
    loadErrorMessage,
    isOffline,
    notice,
    records,
    reflection,
    isReflectionOpen,
    saveState,
    saveStateLabel,
    saveStateDetail,
    saveStateHelper,
    isComplete,
    isControlsDisabled,
    handleReloadDraft,
    handleToggleReflection,
    handleChangeReflection,
    handleBlurReflection,
    handleRetrySaveReflection,
    handleSelectPhoto,
    handleRetryPhoto,
    handleRemovePhoto,
  }
}

function clearTimerRef(timerRef: { current: ReturnType<typeof setTimeout> | null }) {
  if (timerRef.current === null) return
  clearTimeout(timerRef.current)
  timerRef.current = null
}

function formatPhotoSize(sizeBytes: number): string {
  if (sizeBytes < 1024 * 1024) return `${Math.max(1, Math.round(sizeBytes / 1024))} KB`
  return `${SIZE_FORMATTER.format(sizeBytes / (1024 * 1024))} MB`
}
