import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AppError } from '@/core/errors/app-error'
import type {
  ReactFastifyPracticeRunner,
  ReactFastifyPracticeStatus,
} from '@/core/learning/react-fastify-practice-runner'
import type { ReactQuestionProps } from '../react-question/use-react-question'
import { validateReactAdditionalFile } from '@/core/learning/react-question-draft/react-question-draft-store'
import type { ReactQuestionDraftKey } from '@/core/learning/react-question-draft/react-question-draft-store'
import type { ReactFastifyQuestion as ReactQuestionModel } from '@/core/learning/choice-activity'

export type ReactFastifyQuestionProps = Omit<
  ReactQuestionProps,
  'question' | 'runnerFactory'
> & {
  question: ReactQuestionModel
  runnerFactory?: () => ReactFastifyPracticeRunner
}

const MAX_SOURCE_BYTES = 256 * 1024

function sourceSize(files: readonly { path: string; content: string }[]) {
  const encoder = new TextEncoder()
  return files.reduce(
    (size, file) =>
      size +
      encoder.encode(file.path).byteLength +
      encoder.encode(file.content).byteLength,
    0,
  )
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
    ReactFastifyQuestionProps,
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

export function useReactFastifyQuestion(props: ReactFastifyQuestionProps) {
  const questionSignature = JSON.stringify(props.question)
  const question = useMemo(
    () => JSON.parse(questionSignature) as ReactQuestionModel,
    [questionSignature],
  )
  const draftStore = props.draftStore
  const editablePaths = useMemo(
    () =>
      new Set(
        question.initialFiles
          .filter((file) => file.editable && question.editablePaths.includes(file.path))
          .map((file) => file.path),
      ),
    [question.editablePaths, question.initialFiles],
  )
  const initialFiles = useMemo(
    () =>
      question.initialFiles
        .filter((file) => editablePaths.has(file.path))
        .map(({ path, content }) => ({ path, content })),
    [editablePaths, question.initialFiles],
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
        questionKey: question.key,
        skillId: props.skillId,
      }),
    [
      props.accountId,
      props.activityId,
      props.activityRevision,
      props.isDiagnostic,
      props.competencyId,
      props.goalId,
      question.key,
      props.skillId,
    ],
  )
  const activeQuestionKeysKey = props.activeQuestionKeys.join('\u001f')
  const [files, setFiles] = useState(initialFiles)
  const filesRef = useRef(files)
  filesRef.current = files
  const [selectedPath, setSelectedPath] = useState(question.initialFiles[0]?.path ?? '')
  const [draftLoaded, setDraftLoaded] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [hasSaveError, setHasSaveError] = useState(false)
  const [isAssessing, setIsAssessing] = useState(false)
  const [hasAssessError, setHasAssessError] = useState(false)
  const [frontendStatus, setFrontendStatus] = useState<ReactFastifyPracticeStatus>('idle')
  const [apiStatus, setApiStatus] = useState<ReactFastifyPracticeStatus>('idle')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [terminalText, setTerminalText] = useState('')
  const [newFilePath, setNewFilePath] = useState('')
  const [hasFileError, setHasFileError] = useState(false)
  const [isDraftInvalidated, setIsDraftInvalidated] = useState(false)
  const [runnerRevision, setRunnerRevision] = useState(0)
  const runnerRef = useRef<ReactFastifyPracticeRunner | null>(null)
  const onFilesChangeRef = useRef(props.onFilesChange)
  const onAnswerValidityChangeRef = useRef(props.onAnswerValidityChange)
  onFilesChangeRef.current = props.onFilesChange
  onAnswerValidityChangeRef.current = props.onAnswerValidityChange
  const draftGenerationRef = useRef(0)
  const saveQueueRef = useRef<Promise<unknown>>(Promise.resolve())
  const editVersionRef = useRef(0)
  const scopeVersionRef = useRef(0)
  const restoredScopeRef = useRef<string | null>(null)
  const initializedScopeRef = useRef<string | null>(null)
  const saveTimeoutRef = useRef<number | null>(null)
  const isDraftInvalidatedRef = useRef(false)
  const isActivityLocked = props.canSubmit === false
  const isFrozen = Boolean(
    props.readOnly || props.disabled || isAssessing || isActivityLocked,
  )
  const isFrozenRef = useRef(isFrozen)
  isFrozenRef.current = isFrozen
  const scopeKey = JSON.stringify([draftKey, question])
  const activeScopeRef = useRef(scopeKey)
  activeScopeRef.current = scopeKey
  const displayFiles = useMemo(() => getProjectFiles(files, question), [files, question])
  const editorEditablePaths = useMemo(
    () => [
      ...editablePaths,
      ...files
        .filter(
          (file) => !question.initialFiles.some((initial) => initial.path === file.path),
        )
        .map(({ path }) => path),
    ],
    [editablePaths, files, question.initialFiles],
  )
  const additionalFilesCount = files.filter(
    (file) => !question.initialFiles.some((initial) => initial.path === file.path),
  ).length
  const totalSourceBytes = sourceSize(displayFiles)

  useEffect(
    () => () => {
      scopeVersionRef.current += 1
    },
    [],
  )

  useEffect(() => {
    let cancelled = false
    if (initializedScopeRef.current !== scopeKey) {
      initializedScopeRef.current = scopeKey
      restoredScopeRef.current = null
      scopeVersionRef.current += 1
      setDraftLoaded(false)
      setFiles(initialFiles)
      filesRef.current = initialFiles
      setSelectedPath(question.initialFiles[0]?.path ?? '')
      draftGenerationRef.current = 0
      editVersionRef.current = 0
      isDraftInvalidatedRef.current = false
      setIsDraftInvalidated(false)
      setHasSaveError(false)
    }
    if (restoredScopeRef.current === scopeKey) return
    if (!draftKey) {
      restoredScopeRef.current = scopeKey
      setDraftLoaded(true)
      return
    }
    if (!props.isOnlineAuthority || !navigator.onLine || isActivityLocked) return
    const scopeVersion = ++scopeVersionRef.current
    void draftStore
      .read(draftKey)
      .then(async (draft) => {
        if (cancelled) return
        if (draft?.tombstone) {
          isDraftInvalidatedRef.current = true
          setIsDraftInvalidated(true)
          const generation = await draftStore.clearTombstone(
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
        if (draft && validRestoredFiles(draft.files, question)) {
          setFiles(copyFiles(draft.files))
          setSelectedPath(draft.files[0]?.path ?? '')
          draftGenerationRef.current = draft.generation
        } else if (draft) {
          const generation = await draftStore.tombstone(draftKey)
          const freshGeneration = await draftStore.clearTombstone(
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
        if (!cancelled && scopeVersion === scopeVersionRef.current) {
          restoredScopeRef.current = scopeKey
          setDraftLoaded(true)
        }
      })
    return () => {
      cancelled = true
    }
  }, [
    draftKey,
    draftStore,
    initialFiles,
    isActivityLocked,
    props.isOnlineAuthority,
    question,
    scopeKey,
  ])

  const queueSave = useCallback(
    function queueSave(
      snapshot: readonly { path: string; content: string }[],
      version: number,
      forAssessment = false,
    ) {
      const key = draftKey
      const scopeVersion = scopeVersionRef.current
      if (!key) return Promise.resolve(true)
      const operation = saveQueueRef.current
        .catch(() => undefined)
        .then(async () => {
          if (
            scopeVersion !== scopeVersionRef.current ||
            activeScopeRef.current !== scopeKey ||
            isDraftInvalidatedRef.current ||
            (!forAssessment && version !== editVersionRef.current)
          )
            return false
          const generation = await draftStore.write(
            key,
            snapshot,
            draftGenerationRef.current,
          )
          if (
            scopeVersion !== scopeVersionRef.current ||
            activeScopeRef.current !== scopeKey ||
            isDraftInvalidatedRef.current
          )
            return false
          if (generation > 0) {
            draftGenerationRef.current = Math.max(draftGenerationRef.current, generation)
            setHasSaveError(false)
            return true
          }
          const latest = await draftStore.read(key)
          if (
            scopeVersion !== scopeVersionRef.current ||
            activeScopeRef.current !== scopeKey
          )
            return false
          if (
            !latest ||
            latest.tombstone ||
            !validRestoredFiles(latest.files, question)
          ) {
            isDraftInvalidatedRef.current = true
            setIsDraftInvalidated(true)
            onAnswerValidityChangeRef.current?.(false)
            return false
          }
          if (areFilesEqual(latest.files, snapshot)) {
            draftGenerationRef.current = latest.generation
            return true
          }
          if (forAssessment || isFrozenRef.current) {
            isDraftInvalidatedRef.current = true
            setIsDraftInvalidated(true)
            onAnswerValidityChangeRef.current?.(false)
            return false
          }
          if (version === editVersionRef.current && !isFrozenRef.current) {
            draftGenerationRef.current = latest.generation
            editVersionRef.current += 1
            filesRef.current = copyFiles(latest.files)
            setFiles(copyFiles(latest.files))
            setSelectedPath(latest.files[0]?.path ?? '')
            onFilesChangeRef.current?.(copyFiles(latest.files))
            setRunnerRevision((revision) => revision + 1)
          }
          return false
        })
      saveQueueRef.current = operation
      return operation
    },
    [draftKey, draftStore, question, scopeKey],
  )

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
    const version = editVersionRef.current
    const timeout = window.setTimeout(() => {
      saveTimeoutRef.current = null
      void queueSave(copyFiles(files), version)
        .catch(() => setHasSaveError(true))
        .finally(() => {
          if (version === editVersionRef.current) setIsSaving(false)
        })
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
    queueSave,
  ])

  useEffect(() => {
    if (!draftKey) return
    let cancelled = false
    const unsubscribe = draftStore.subscribe(draftKey, (event) => {
      void draftStore
        .read(draftKey)
        .then((draft) => {
          if (
            cancelled ||
            !draft ||
            draft.generation !== event.generation ||
            draft.generation <= draftGenerationRef.current
          )
            return
          if (event.tombstone || draft.tombstone) {
            draftGenerationRef.current = draft.generation
            isDraftInvalidatedRef.current = true
            setIsDraftInvalidated(true)
            setFiles(initialFiles)
            setSelectedPath(initialFiles[0]?.path ?? '')
            onAnswerValidityChangeRef.current?.(false)
            return
          }
          if (isFrozenRef.current) return
          if (validRestoredFiles(draft.files, question)) {
            draftGenerationRef.current = draft.generation
            editVersionRef.current += 1
            if (saveTimeoutRef.current !== null) {
              window.clearTimeout(saveTimeoutRef.current)
              saveTimeoutRef.current = null
            }
            if (!areFilesEqual(filesRef.current, draft.files)) {
              filesRef.current = copyFiles(draft.files)
              setFiles(copyFiles(draft.files))
              setSelectedPath(draft.files[0]?.path ?? '')
              onFilesChangeRef.current?.(copyFiles(draft.files))
              setRunnerRevision((revision) => revision + 1)
            }
            onAnswerValidityChangeRef.current?.(true)
          }
        })
        .catch(() => setHasSaveError(true))
    })
    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [draftKey, draftStore, initialFiles, question])

  useEffect(() => {
    if (isActivityLocked) {
      onAnswerValidityChangeRef.current?.(false)
      return
    }
    if (!draftLoaded || (draftKey && !props.isOnlineAuthority)) return
    const isValid = !isDraftInvalidated && validRestoredFiles(files, question)
    onAnswerValidityChangeRef.current?.(isValid)
    if (isValid) onFilesChangeRef.current?.(copyFiles(files))
  }, [
    draftKey,
    draftLoaded,
    files,
    isActivityLocked,
    isDraftInvalidated,
    props.isOnlineAuthority,
    question,
  ])

  useEffect(() => {
    if (!draftKey || !props.isOnlineAuthority || !props.activityRevision) return
    void draftStore
      .tombstoneStaleActivity(
        draftKey,
        props.activityRevision,
        activeQuestionKeysKey.split('\u001f'),
      )
      .catch(() => setHasSaveError(true))
  }, [
    activeQuestionKeysKey,
    draftKey,
    draftStore,
    props.activityRevision,
    props.isOnlineAuthority,
  ])

  useEffect(() => {
    if (draftKey && !props.isOnlineAuthority) onAnswerValidityChangeRef.current?.(false)
  }, [draftKey, props.isOnlineAuthority])

  // biome-ignore lint/correctness/useExhaustiveDependencies: Remote adoption restarts the sandbox so removed files cannot remain in the preview.
  useEffect(() => {
    const factory = props.runnerFactory
    if (!factory || !props.isOnlineAuthority || !draftLoaded || isDraftInvalidated) {
      setFrontendStatus('unavailable')
      setApiStatus('unavailable')
      return
    }
    const runner = factory()
    let active = true
    runnerRef.current = runner
    const unsubscribe = runner.subscribe((event) => {
      if (!active) return
      setFrontendStatus(event.frontendStatus)
      setApiStatus(event.apiStatus)
      setTerminalText(event.terminalText)
      const safePreview = getSafePreviewUrl(event.previewUrl)
      setPreviewUrl(safePreview)
    })
    const projectFiles = getProjectFiles(filesRef.current, question)
    void runner
      .start({
        files: copyFiles(projectFiles),
        frontendEntrypoint: question.frontendEntrypoint,
        apiEntrypoint: question.apiEntrypoint,
        frontendCommandId: question.frontendCommandId,
        apiCommandId: question.apiCommandId,
        fixedDependencies: question.fixedDependencies,
        permittedCommands: question.permittedCommands,
        additionalFilePolicy: question.additionalFilePolicy ?? undefined,
      })
      .catch(() => {
        setFrontendStatus('unavailable')
        setApiStatus('unavailable')
      })
    return () => {
      active = false
      unsubscribe()
      runner.dispose()
      runnerRef.current = null
      setPreviewUrl(null)
    }
  }, [
    draftLoaded,
    isDraftInvalidated,
    props.isOnlineAuthority,
    question,
    props.runnerFactory,
    runnerRevision,
  ])

  useEffect(() => {
    if (!draftKey) return
    function handleOffline() {
      setPreviewUrl(null)
      setFrontendStatus('unavailable')
      setApiStatus('unavailable')
      onAnswerValidityChangeRef.current?.(false)
    }
    function handleOnline() {
      onAnswerValidityChangeRef.current?.(false)
    }
    window.addEventListener('offline', handleOffline)
    window.addEventListener('online', handleOnline)
    return () => {
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('online', handleOnline)
    }
  }, [draftKey])

  function handleFileChange(path: string, content: string) {
    const isAdditionalFile =
      files.some((file) => file.path === path) &&
      !question.initialFiles.some((file) => file.path === path)
    if (
      isFrozen ||
      isDraftInvalidated ||
      isActivityLocked ||
      (!editablePaths.has(path) && !isAdditionalFile)
    )
      return
    const nextFiles = files.map((file) => (file.path === path ? { path, content } : file))
    if (sourceSize(getProjectFiles(nextFiles, question)) > MAX_SOURCE_BYTES) {
      setHasFileError(true)
      return
    }
    setFiles(nextFiles)
    filesRef.current = nextFiles
    editVersionRef.current += 1
    props.onFilesChange?.(copyFiles(nextFiles))
    if (draftKey && !props.isOnlineAuthority) onAnswerValidityChangeRef.current?.(false)
    else onAnswerValidityChangeRef.current?.(true)
    void runnerRef.current?.updateFile(path, content).catch(() => {
      setFrontendStatus('error')
      setApiStatus('error')
    })
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
        getProjectFiles(files, question),
        question.additionalFilePolicy,
        question.initialFiles.map(({ path: initialPath }) => initialPath),
      )
    ) {
      setHasFileError(true)
      return
    }
    const nextFiles = [...files, { path, content: '' }]
    if (sourceSize(getProjectFiles(nextFiles, question)) > MAX_SOURCE_BYTES) {
      setHasFileError(true)
      return
    }
    setFiles(nextFiles)
    filesRef.current = nextFiles
    editVersionRef.current += 1
    setSelectedPath(path)
    setNewFilePath('')
    setHasFileError(false)
    props.onFilesChange?.(copyFiles(nextFiles))
    if (draftKey && !props.isOnlineAuthority) onAnswerValidityChangeRef.current?.(false)
    else onAnswerValidityChangeRef.current?.(true)
    void runnerRef.current?.addFile({ path, content: '' }).catch(() => {
      setFrontendStatus('error')
      setApiStatus('error')
    })
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
      !validRestoredFiles(files, question)
    )
      return
    setIsAssessing(true)
    isFrozenRef.current = true
    setHasAssessError(false)
    const snapshot = copyFiles(files)
    try {
      if (draftKey) {
        if (saveTimeoutRef.current !== null) {
          window.clearTimeout(saveTimeoutRef.current)
          saveTimeoutRef.current = null
        }
        setIsSaving(true)
        let saved: boolean
        try {
          saved = await queueSave(snapshot, editVersionRef.current, true)
        } catch (error) {
          setHasSaveError(true)
          throw error
        }
        if (!saved) {
          setHasSaveError(true)
          throw new AppError('O rascunho mudou ou foi invalidado em outra aba.')
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
    frontendStatus,
    apiStatus,
    previewUrl,
    terminalText,
    newFilePath,
    hasFileError,
    isDraftInvalidated,
    isActivityLocked,
    totalSourceBytes,
    isFrozen,
    handleRequest: useCallback(
      (
        request: Parameters<ReactFastifyPracticeRunner['request']>[0],
        signal?: AbortSignal,
      ) => {
        const runner = runnerRef.current
        if (!runner)
          return Promise.reject(new AppError('A API de prática está indisponível.'))
        return runner.request(request, signal)
      },
      [],
    ),
    handleRunCommand: useCallback((commandId: string) => {
      const runner = runnerRef.current
      if (!runner) return Promise.reject(new AppError('O terminal está indisponível.'))
      return runner.runCommand(commandId)
    }, []),
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
      Boolean(url.username || url.password) ||
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
