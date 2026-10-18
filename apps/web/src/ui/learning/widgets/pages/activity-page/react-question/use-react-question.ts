import { useEffect, useMemo, useRef, useState } from 'react'
import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import type { ReactPracticeRunner } from '@/core/learning/react-practice-runner'
import {
  ReactQuestionDraftStore,
  validateReactAdditionalFile,
} from '@/core/learning/react-question-draft/react-question-draft-store'
import type { ReactQuestionDraftKey } from '@/core/learning/react-question-draft/react-question-draft-store'
import type { ReactQuestion as ReactQuestionModel } from '@/core/learning/choice-activity'

export type ReactQuestionProps = {
  question: ReactQuestionModel
  accountId: string | null
  goalId?: string
  skillId?: string
  competencyId?: string
  activityId: string
  activityRevision: string | null
  activeQuestionKeys: readonly string[]
  isOnlineAuthority: boolean
  canSubmit?: boolean
  isDiagnostic?: boolean
  activityTitle?: string
  difficulty?: ActivityDifficulty
  questionNumber: number
  totalQuestions: number
  disabled?: boolean
  readOnly?: boolean
  onFilesChange?: (files: readonly { path: string; content: string }[]) => void
  onAnswerValidityChange?: (isValid: boolean) => void
  onAssess?: (files: readonly { path: string; content: string }[]) => void | Promise<void>
  runnerFactory?: () => ReactPracticeRunner
}

const MAX_SOURCE_BYTES = 256 * 1024

function sourceSize(files: readonly { path: string; content: string }[]) {
  return new TextEncoder().encode(
    files.map(({ path, content }) => `${path}\u0000${content}`).join('\u0000'),
  ).byteLength
}

function copyFiles(files: readonly { path: string; content: string }[]) {
  return files.map(({ path, content }) => ({ path, content }))
}

function areFilesEqual(
  first: readonly { path: string; content: string }[],
  second: readonly { path: string; content: string }[],
) {
  return (
    first.length === second.length &&
    first.every(
      (file, index) =>
        file.path === second[index]?.path && file.content === second[index]?.content,
    )
  )
}

function getProjectFiles(
  files: readonly { path: string; content: string }[],
  question: ReactQuestionModel,
) {
  const currentFiles = new Map(files.map((file) => [file.path, file.content]))
  return [
    ...question.initialFiles.map(({ path, content }) => ({
      path,
      content: currentFiles.get(path) ?? content,
    })),
    ...files.filter(
      (file) => !question.initialFiles.some((initial) => initial.path === file.path),
    ),
  ]
}

function getDraftKey(
  props: Pick<
    ReactQuestionProps,
    | 'accountId'
    | 'activityId'
    | 'activityRevision'
    | 'competencyId'
    | 'goalId'
    | 'isDiagnostic'
    | 'skillId'
  > & { questionKey: string },
): ReactQuestionDraftKey | null {
  if (
    !props.accountId ||
    props.isDiagnostic ||
    !props.goalId ||
    !props.skillId ||
    !props.competencyId ||
    !props.activityRevision
  )
    return null
  return {
    accountId: props.accountId,
    goalId: props.goalId,
    skillId: props.skillId,
    competencyId: props.competencyId,
    activityId: props.activityId,
    questionKey: props.questionKey,
    activityRevision: props.activityRevision,
  }
}

function validRestoredFiles(
  files: readonly { path: string; content: string }[],
  question: ReactQuestionModel,
) {
  if (files.length === 0) return false
  const initialFiles = new Map(question.initialFiles.map((file) => [file.path, file]))
  const additionalFilesCount = files.filter((file) => !initialFiles.has(file.path)).length
  if (additionalFilesCount > (question.additionalFilePolicy?.maxFiles ?? 0)) return false
  const seen = new Set<string>()
  for (const file of files) {
    if (seen.has(file.path) || typeof file.content !== 'string') return false
    seen.add(file.path)
    const initial = initialFiles.get(file.path)
    if (initial) {
      if (!initial.editable || !question.editablePaths.includes(file.path)) return false
      continue
    }
    if (
      !validateReactAdditionalFile(
        file.path,
        files.filter((existingFile) => existingFile !== file),
        question.additionalFilePolicy,
        question.initialFiles.map(({ path }) => path),
        false,
      )
    )
      return false
  }
  if (
    question.initialFiles.some(
      (file) =>
        file.editable &&
        question.editablePaths.includes(file.path) &&
        !seen.has(file.path),
    )
  )
    return false
  return sourceSize(getProjectFiles(files, question)) <= MAX_SOURCE_BYTES
}

export function useReactQuestion(props: ReactQuestionProps) {
  const editablePaths = useMemo(
    () =>
      new Set(
        props.question.initialFiles
          .filter(
            (file) => file.editable && props.question.editablePaths.includes(file.path),
          )
          .map((file) => file.path),
      ),
    [props.question.editablePaths, props.question.initialFiles],
  )
  const initialFiles = useMemo(
    () =>
      props.question.initialFiles
        .filter((file) => editablePaths.has(file.path))
        .map(({ path, content }) => ({ path, content })),
    [editablePaths, props.question.initialFiles],
  )
  const draftKey = useMemo(
    () =>
      getDraftKey({
        accountId: props.accountId,
        activityId: props.activityId,
        activityRevision: props.activityRevision,
        competencyId: props.competencyId,
        goalId: props.goalId,
        isDiagnostic: props.isDiagnostic,
        questionKey: props.question.key,
        skillId: props.skillId,
      }),
    [
      props.accountId,
      props.activityId,
      props.activityRevision,
      props.isDiagnostic,
      props.competencyId,
      props.goalId,
      props.question.key,
      props.skillId,
    ],
  )
  const activeQuestionKeysKey = props.activeQuestionKeys.join('\u001f')
  const [files, setFiles] = useState(initialFiles)
  const filesRef = useRef(files)
  filesRef.current = files
  const [selectedPath, setSelectedPath] = useState(
    props.question.initialFiles[0]?.path ?? '',
  )
  const [draftLoaded, setDraftLoaded] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [hasSaveError, setHasSaveError] = useState(false)
  const [isAssessing, setIsAssessing] = useState(false)
  const [hasAssessError, setHasAssessError] = useState(false)
  const [status, setStatus] = useState<'idle' | 'booting' | 'ready' | 'unavailable'>(
    'idle',
  )
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [terminalText, setTerminalText] = useState('')
  const [newFilePath, setNewFilePath] = useState('')
  const [hasFileError, setHasFileError] = useState(false)
  const [isDraftInvalidated, setIsDraftInvalidated] = useState(false)
  const runnerRef = useRef<ReactPracticeRunner | null>(null)
  const onFilesChangeRef = useRef(props.onFilesChange)
  const onAnswerValidityChangeRef = useRef(props.onAnswerValidityChange)
  onFilesChangeRef.current = props.onFilesChange
  onAnswerValidityChangeRef.current = props.onAnswerValidityChange
  const draftGenerationRef = useRef(0)
  const saveTimeoutRef = useRef<number | null>(null)
  const isDraftInvalidatedRef = useRef(false)
  const isActivityLocked = props.canSubmit === false
  const isFrozen = Boolean(
    props.readOnly || props.disabled || isAssessing || isActivityLocked,
  )
  const displayFiles = useMemo(
    () => getProjectFiles(files, props.question),
    [files, props.question],
  )
  const editorEditablePaths = useMemo(
    () => [
      ...editablePaths,
      ...files
        .filter(
          (file) =>
            !props.question.initialFiles.some((initial) => initial.path === file.path),
        )
        .map(({ path }) => path),
    ],
    [editablePaths, files, props.question.initialFiles],
  )
  const additionalFilesCount = files.filter(
    (file) => !props.question.initialFiles.some((initial) => initial.path === file.path),
  ).length
  const totalSourceBytes = sourceSize(displayFiles)

  useEffect(() => {
    let cancelled = false
    setDraftLoaded(false)
    setFiles(initialFiles)
    setSelectedPath(props.question.initialFiles[0]?.path ?? '')
    isDraftInvalidatedRef.current = false
    setIsDraftInvalidated(false)
    if (!draftKey || !props.isOnlineAuthority || !navigator.onLine || isActivityLocked) {
      setDraftLoaded(true)
      return
    }
    void ReactQuestionDraftStore.read(draftKey)
      .then(async (draft) => {
        if (cancelled) return
        if (draft?.tombstone) {
          isDraftInvalidatedRef.current = true
          setIsDraftInvalidated(true)
          const generation = await ReactQuestionDraftStore.clearTombstone(
            draftKey,
            initialFiles,
            draft.generation,
          )
          if (cancelled) return
          if (generation === 0) return
          draftGenerationRef.current = generation
          isDraftInvalidatedRef.current = false
          setIsDraftInvalidated(false)
          return
        }
        if (draft && validRestoredFiles(draft.files, props.question)) {
          setFiles(copyFiles(draft.files))
          setSelectedPath(draft.files[0]?.path ?? '')
          draftGenerationRef.current = draft.generation
        } else if (draft) {
          const generation = await ReactQuestionDraftStore.tombstone(draftKey)
          const freshGeneration = await ReactQuestionDraftStore.clearTombstone(
            draftKey,
            initialFiles,
            generation,
          )
          if (cancelled) return
          if (freshGeneration === 0) return
          draftGenerationRef.current = freshGeneration
        }
      })
      .catch(() => setHasSaveError(true))
      .finally(() => {
        if (!cancelled) setDraftLoaded(true)
      })
    return () => {
      cancelled = true
    }
  }, [draftKey, initialFiles, isActivityLocked, props.isOnlineAuthority, props.question])

  useEffect(() => {
    if (
      !draftKey ||
      !props.isOnlineAuthority ||
      !draftLoaded ||
      isFrozen ||
      isDraftInvalidated ||
      isActivityLocked
    )
      return
    setIsSaving(true)
    const expectedGeneration = draftGenerationRef.current
    const timeout = window.setTimeout(() => {
      saveTimeoutRef.current = null
      void ReactQuestionDraftStore.write(draftKey, files, expectedGeneration)
        .then((generation) => {
          if (generation === 0) {
            return ReactQuestionDraftStore.read(draftKey).then((latest) => {
              if (!latest || latest.tombstone) {
                isDraftInvalidatedRef.current = true
                setIsDraftInvalidated(true)
                onAnswerValidityChangeRef.current?.(false)
                return
              }
              draftGenerationRef.current = latest.generation
              if (!areFilesEqual(latest.files, files)) {
                setFiles(copyFiles(latest.files))
                setSelectedPath(latest.files[0]?.path ?? '')
                onFilesChangeRef.current?.(copyFiles(latest.files))
              }
              onAnswerValidityChangeRef.current?.(true)
            })
          }
          draftGenerationRef.current = generation
          setHasSaveError(false)
        })
        .catch(() => setHasSaveError(true))
        .finally(() => setIsSaving(false))
    }, 350)
    saveTimeoutRef.current = timeout
    return () => {
      window.clearTimeout(timeout)
      if (saveTimeoutRef.current === timeout) saveTimeoutRef.current = null
    }
  }, [
    draftKey,
    draftLoaded,
    files,
    isActivityLocked,
    isDraftInvalidated,
    isFrozen,
    props.isOnlineAuthority,
  ])

  useEffect(() => {
    if (!draftKey) return
    return ReactQuestionDraftStore.subscribe(draftKey, (event) => {
      void ReactQuestionDraftStore.read(draftKey)
        .then((draft) => {
          if (
            !draft ||
            draft.generation !== event.generation ||
            draft.generation <= draftGenerationRef.current
          )
            return
          draftGenerationRef.current = draft.generation
          if (event.tombstone || draft.tombstone) {
            isDraftInvalidatedRef.current = true
            setIsDraftInvalidated(true)
            setFiles(initialFiles)
            setSelectedPath(initialFiles[0]?.path ?? '')
            onAnswerValidityChangeRef.current?.(false)
            return
          }
          if (validRestoredFiles(draft.files, props.question)) {
            if (!areFilesEqual(filesRef.current, draft.files)) {
              setFiles(copyFiles(draft.files))
              setSelectedPath(draft.files[0]?.path ?? '')
              onFilesChangeRef.current?.(copyFiles(draft.files))
            }
            onAnswerValidityChangeRef.current?.(true)
          }
        })
        .catch(() => setHasSaveError(true))
    })
  }, [draftKey, initialFiles, props.question])

  useEffect(() => {
    if (isActivityLocked) {
      onAnswerValidityChangeRef.current?.(false)
      return
    }
    if (!draftLoaded || (draftKey && !props.isOnlineAuthority)) return
    const isValid = !isDraftInvalidated && validRestoredFiles(files, props.question)
    onAnswerValidityChangeRef.current?.(isValid)
    if (isValid) onFilesChangeRef.current?.(copyFiles(files))
  }, [
    draftKey,
    draftLoaded,
    files,
    isActivityLocked,
    isDraftInvalidated,
    props.isOnlineAuthority,
    props.question,
  ])

  useEffect(() => {
    if (!draftKey || !props.isOnlineAuthority || !props.activityRevision) return
    void ReactQuestionDraftStore.tombstoneStaleActivity(
      draftKey,
      props.activityRevision,
      activeQuestionKeysKey.split('\u001f'),
    )
  }, [activeQuestionKeysKey, draftKey, props.activityRevision, props.isOnlineAuthority])

  useEffect(() => {
    if (draftKey && !props.isOnlineAuthority) onAnswerValidityChangeRef.current?.(false)
  }, [draftKey, props.isOnlineAuthority])

  useEffect(() => {
    const factory = props.runnerFactory
    if (!factory || !props.isOnlineAuthority || !draftLoaded) {
      setStatus('unavailable')
      return
    }
    const runner = factory()
    runnerRef.current = runner
    const unsubscribe = runner.subscribe((event) => {
      setStatus(event.status)
      setTerminalText(event.terminalText)
      const safePreview = getSafePreviewUrl(event.previewUrl)
      setPreviewUrl(safePreview)
    })
    const projectFiles = getProjectFiles(filesRef.current, props.question)
    void runner
      .start({
        files: copyFiles(projectFiles),
        entrypoint: props.question.entrypoint,
        fixedDependencies: props.question.fixedDependencies,
        permittedCommands: props.question.permittedCommands,
        additionalFilePolicy: props.question.additionalFilePolicy ?? undefined,
      })
      .catch(() => setStatus('unavailable'))
    return () => {
      unsubscribe()
      runner.dispose()
      runnerRef.current = null
    }
  }, [draftLoaded, props.isOnlineAuthority, props.question, props.runnerFactory])

  useEffect(() => {
    if (!draftKey) return
    function handleOffline() {
      setPreviewUrl(null)
      setStatus('unavailable')
      onAnswerValidityChangeRef.current?.(false)
    }
    function handleOnline() {
      if (props.isOnlineAuthority) onAnswerValidityChangeRef.current?.(true)
    }
    window.addEventListener('offline', handleOffline)
    window.addEventListener('online', handleOnline)
    return () => {
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('online', handleOnline)
    }
  }, [draftKey, props.isOnlineAuthority])

  function handleFileChange(path: string, content: string) {
    const isAdditionalFile =
      files.some((file) => file.path === path) &&
      !props.question.initialFiles.some((file) => file.path === path)
    if (
      isFrozen ||
      isDraftInvalidated ||
      isActivityLocked ||
      (!editablePaths.has(path) && !isAdditionalFile)
    )
      return
    const nextFiles = files.map((file) => (file.path === path ? { path, content } : file))
    if (sourceSize(getProjectFiles(nextFiles, props.question)) > MAX_SOURCE_BYTES) {
      setHasFileError(true)
      return
    }
    setFiles(nextFiles)
    props.onFilesChange?.(copyFiles(nextFiles))
    if (draftKey && !props.isOnlineAuthority) onAnswerValidityChangeRef.current?.(false)
    else onAnswerValidityChangeRef.current?.(true)
    void runnerRef.current?.updateFile(path, content)
    setHasFileError(false)
  }

  function handleAddFile() {
    const path = newFilePath.trim()
    if (
      isFrozen ||
      isDraftInvalidated ||
      isActivityLocked ||
      !validateReactAdditionalFile(
        path,
        getProjectFiles(files, props.question),
        props.question.additionalFilePolicy,
        props.question.initialFiles.map(({ path: initialPath }) => initialPath),
      )
    ) {
      setHasFileError(true)
      return
    }
    const nextFiles = [...files, { path, content: '' }]
    if (sourceSize(getProjectFiles(nextFiles, props.question)) > MAX_SOURCE_BYTES) {
      setHasFileError(true)
      return
    }
    setFiles(nextFiles)
    setSelectedPath(path)
    setNewFilePath('')
    setHasFileError(false)
    props.onFilesChange?.(copyFiles(nextFiles))
    if (draftKey && !props.isOnlineAuthority) onAnswerValidityChangeRef.current?.(false)
    else onAnswerValidityChangeRef.current?.(true)
    void runnerRef.current?.addFile({ path, content: '' })
  }

  async function handleAssess() {
    if (
      isFrozen ||
      isDraftInvalidated ||
      isActivityLocked ||
      !props.onAssess ||
      !draftLoaded ||
      !props.isOnlineAuthority ||
      !navigator.onLine ||
      !validRestoredFiles(files, props.question)
    )
      return
    setIsAssessing(true)
    setHasAssessError(false)
    const snapshot = copyFiles(files)
    try {
      if (draftKey) {
        if (saveTimeoutRef.current !== null) {
          window.clearTimeout(saveTimeoutRef.current)
          saveTimeoutRef.current = null
        }
        setIsSaving(true)
        let generation: number
        try {
          generation = await ReactQuestionDraftStore.write(
            draftKey,
            snapshot,
            draftGenerationRef.current,
          )
        } catch (error) {
          setHasSaveError(true)
          throw error
        }
        if (generation === 0) {
          const latest = await ReactQuestionDraftStore.read(draftKey)
          if (!latest || latest.tombstone || !areFilesEqual(latest.files, snapshot)) {
            isDraftInvalidatedRef.current = true
            setIsDraftInvalidated(true)
            setHasSaveError(true)
            throw new Error('O rascunho mudou ou foi invalidado em outra aba.')
          }
          draftGenerationRef.current = latest.generation
        } else {
          draftGenerationRef.current = generation
        }
        setIsSaving(false)
      }
      await props.onAssess(snapshot)
    } catch {
      setHasAssessError(true)
    } finally {
      setIsSaving(false)
      setIsAssessing(false)
    }
  }

  return {
    files,
    displayFiles,
    selectedPath,
    editablePaths: [...editablePaths],
    editorEditablePaths,
    additionalFilesCount,
    draftLoaded,
    draftGeneration: draftGenerationRef.current,
    isSaving,
    hasSaveError,
    isAssessing,
    hasAssessError,
    status,
    previewUrl,
    terminalText,
    newFilePath,
    hasFileError,
    isDraftInvalidated,
    isActivityLocked,
    totalSourceBytes,
    isFrozen,
    handleAddFile,
    handleAssess,
    handleFileChange,
    handleSelectFile: setSelectedPath,
    handleNewFilePathChange: setNewFilePath,
  }
}

function getSafePreviewUrl(value: string | null) {
  if (!value) return null
  try {
    const url = new URL(value)
    if (
      url.protocol !== 'https:' ||
      (!url.hostname.endsWith('.webcontainer.io') &&
        !url.hostname.endsWith('.webcontainer-api.io')) ||
      url.origin === window.location.origin
    )
      return null
    return url.href
  } catch {
    return null
  }
}
