import { useEffect, useMemo, useRef, useState } from 'react'
import type { HtmlCssJsQuestion as HtmlQuestion } from '@/core/learning/choice-activity'
import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import type { HtmlCssJsPracticeRunner } from '@/core/learning/html-css-js-practice-runner'
import type { ReactQuestionDraftStore } from '@/core/learning/react-question-draft/react-question-draft-store'

export type HtmlCssJsQuestionProps = {
  question: HtmlQuestion
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
  draftStore: ReactQuestionDraftStore
  runnerFactory?: () => HtmlCssJsPracticeRunner
  onFilesChange?: (files: readonly { path: string; content: string }[]) => void
  onAnswerValidityChange?: (isValid: boolean) => void
  onAssess?: (files: readonly { path: string; content: string }[]) => void | Promise<void>
}

const MAX_SOURCE_BYTES = 256 * 1024

function copyFiles(files: readonly { path: string; content: string }[]) {
  return files.map(({ path, content }) => ({ path, content }))
}

function getEditableInitialFiles(question: HtmlQuestion) {
  return question.initialFiles
    .filter(({ path, editable }) => editable && question.editablePaths.includes(path))
    .map(({ path, content }) => ({ path, content }))
}

function getProjectFiles(
  files: readonly { path: string; content: string }[],
  question: HtmlQuestion,
) {
  const editedFiles = new Map(files.map(({ path, content }) => [path, content]))
  return question.initialFiles.map(({ path, content }) => ({
    path,
    content: editedFiles.get(path) ?? content,
  }))
}

function sourceSize(files: readonly { path: string; content: string }[]) {
  return files.reduce(
    (total, file) =>
      total +
      new TextEncoder().encode(file.path).byteLength +
      new TextEncoder().encode(file.content).byteLength,
    0,
  )
}

function matchesEditableFiles(
  files: readonly { path: string; content: string }[],
  question: HtmlQuestion,
) {
  const allowed = new Set(getEditableInitialFiles(question).map(({ path }) => path))
  return (
    files.length === allowed.size &&
    files.every(({ path }) => allowed.has(path)) &&
    sourceSize(files) <= MAX_SOURCE_BYTES
  )
}

export function useHtmlCssJsQuestion(props: HtmlCssJsQuestionProps) {
  const initialFiles = useMemo(
    () => getEditableInitialFiles(props.question),
    [props.question],
  )
  const draftKey = useMemo(() => {
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
      questionKey: props.question.key,
      activityRevision: props.activityRevision,
    }
  }, [
    props.accountId,
    props.activityId,
    props.activityRevision,
    props.competencyId,
    props.goalId,
    props.isDiagnostic,
    props.question.key,
    props.skillId,
  ])
  const [files, setFiles] = useState(initialFiles)
  const filesRef = useRef(files)
  filesRef.current = files
  const [selectedPath, setSelectedPath] = useState(initialFiles[0]?.path ?? '')
  const [draftLoaded, setDraftLoaded] = useState(false)
  const [generation, setGeneration] = useState(0)
  const generationRef = useRef(0)
  const [isSaving, setIsSaving] = useState(false)
  const [hasSaveError, setHasSaveError] = useState(false)
  const [isDraftInvalidated, setIsDraftInvalidated] = useState(false)
  const [practiceStatus, setPracticeStatus] = useState<
    'idle' | 'booting' | 'ready' | 'unavailable'
  >('idle')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [terminalText, setTerminalText] = useState('')
  const [practiceTab, setPracticeTab] = useState<'preview' | 'terminal'>('preview')
  const [hasAssessError, setHasAssessError] = useState(false)
  const [isAssessing, setIsAssessing] = useState(false)
  const [editVersion, setEditVersion] = useState(0)
  const [runnerRevision, setRunnerRevision] = useState(0)
  const [hasFileError, setHasFileError] = useState(false)
  const isFrozen = Boolean(
    props.disabled ||
      props.readOnly ||
      props.canSubmit === false ||
      isAssessing ||
      isDraftInvalidated,
  )
  const activeQuestionKeys = props.activeQuestionKeys.join('\u001f')
  const scopeKey = JSON.stringify([draftKey, props.question])
  const loadedScopeRef = useRef<string | null>(null)
  const writeQueueRef = useRef<Promise<unknown>>(Promise.resolve())
  const runnerRef = useRef<HtmlCssJsPracticeRunner | null>(null)
  const saveTimeoutRef = useRef<number | null>(null)
  const scopeVersionRef = useRef(0)
  const currentScopeRef = useRef(scopeKey)
  currentScopeRef.current = scopeKey
  const onFilesChangeRef = useRef(props.onFilesChange)
  const onValidityChangeRef = useRef(props.onAnswerValidityChange)
  onFilesChangeRef.current = props.onFilesChange
  onValidityChangeRef.current = props.onAnswerValidityChange

  useEffect(() => {
    let cancelled = false
    if (loadedScopeRef.current !== scopeKey) {
      loadedScopeRef.current = null
      scopeVersionRef.current += 1
      generationRef.current = 0
      setGeneration(0)
      setDraftLoaded(false)
      setIsDraftInvalidated(false)
      setHasSaveError(false)
      setFiles(initialFiles)
      filesRef.current = initialFiles
      setSelectedPath(initialFiles[0]?.path ?? '')
    }
    if (!draftKey) {
      loadedScopeRef.current = scopeKey
      setDraftLoaded(true)
      return
    }
    if (!props.isOnlineAuthority || !navigator.onLine || props.disabled) return
    const scopeVersion = ++scopeVersionRef.current
    void props.draftStore
      .read(draftKey)
      .then(async (draft) => {
        if (cancelled || scopeVersion !== scopeVersionRef.current) return
        if (draft?.tombstone) {
          setIsDraftInvalidated(true)
          const nextGeneration = await props.draftStore.clearTombstone(
            draftKey,
            initialFiles,
            draft.generation,
          )
          if (
            cancelled ||
            scopeVersion !== scopeVersionRef.current ||
            nextGeneration === 0
          )
            return
          generationRef.current = nextGeneration
          setGeneration(nextGeneration)
          setIsDraftInvalidated(false)
        } else if (draft && matchesEditableFiles(draft.files, props.question)) {
          const restored = copyFiles(draft.files)
          setFiles(restored)
          filesRef.current = restored
          setSelectedPath(restored[0]?.path ?? '')
          generationRef.current = draft.generation
          setGeneration(draft.generation)
        } else if (draft) {
          const removedGeneration = await props.draftStore.tombstone(draftKey)
          const nextGeneration = await props.draftStore.clearTombstone(
            draftKey,
            initialFiles,
            removedGeneration,
          )
          if (
            cancelled ||
            scopeVersion !== scopeVersionRef.current ||
            nextGeneration === 0
          )
            return
          generationRef.current = nextGeneration
          setGeneration(nextGeneration)
        }
      })
      .catch(() => setHasSaveError(true))
      .finally(() => {
        if (!cancelled && scopeVersion === scopeVersionRef.current) {
          loadedScopeRef.current = scopeKey
          setDraftLoaded(true)
        }
      })
    return () => {
      cancelled = true
    }
  }, [
    draftKey,
    initialFiles,
    props.disabled,
    props.draftStore,
    props.isOnlineAuthority,
    props.question,
    scopeKey,
  ])

  useEffect(() => {
    if (
      !draftKey ||
      !props.isOnlineAuthority ||
      !draftLoaded ||
      isFrozen ||
      !navigator.onLine
    )
      return
    setIsSaving(true)
    const version = editVersion
    const scopeVersion = scopeVersionRef.current
    const timeout = window.setTimeout(() => {
      saveTimeoutRef.current = null
      const write = writeQueueRef.current
        .catch(() => undefined)
        .then(async () => {
          if (
            scopeVersion !== scopeVersionRef.current ||
            currentScopeRef.current !== scopeKey ||
            isDraftInvalidated ||
            version !== editVersion
          )
            return
          const nextGeneration = await props.draftStore.write(
            draftKey,
            copyFiles(filesRef.current),
            generationRef.current,
          )
          if (currentScopeRef.current !== scopeKey || isDraftInvalidated) return
          if (nextGeneration > 0) {
            generationRef.current = nextGeneration
            setGeneration(nextGeneration)
            setHasSaveError(false)
            return
          }
          const latest = await props.draftStore.read(draftKey)
          if (
            latest?.tombstone ||
            !latest ||
            !matchesEditableFiles(latest.files, props.question)
          ) {
            setIsDraftInvalidated(true)
            return
          }
          generationRef.current = latest.generation
          setGeneration(latest.generation)
          if (version === editVersion && !isFrozen) {
            const adopted = copyFiles(latest.files)
            filesRef.current = adopted
            setFiles(adopted)
            setSelectedPath(adopted[0]?.path ?? '')
            onFilesChangeRef.current?.(adopted)
            setRunnerRevision((value) => value + 1)
          }
        })
      writeQueueRef.current = write
      void write
        .catch(() => setHasSaveError(true))
        .finally(() => {
          if (version === editVersion) setIsSaving(false)
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
    editVersion,
    isDraftInvalidated,
    isFrozen,
    props.draftStore,
    props.isOnlineAuthority,
    props.question,
    scopeKey,
  ])

  useEffect(() => {
    if (!draftKey) return
    let cancelled = false
    const unsubscribe = props.draftStore.subscribe(draftKey, (event) => {
      void props.draftStore
        .read(draftKey)
        .then((draft) => {
          if (
            cancelled ||
            !draft ||
            draft.generation !== event.generation ||
            draft.generation <= generationRef.current
          )
            return
          if (event.tombstone || draft.tombstone) {
            generationRef.current = draft.generation
            setGeneration(draft.generation)
            setIsDraftInvalidated(true)
            return
          }
          if (!isFrozen && matchesEditableFiles(draft.files, props.question)) {
            const adopted = copyFiles(draft.files)
            generationRef.current = draft.generation
            setGeneration(draft.generation)
            setEditVersion((version) => version + 1)
            filesRef.current = adopted
            setFiles(adopted)
            setSelectedPath(adopted[0]?.path ?? '')
            onFilesChangeRef.current?.(adopted)
            setRunnerRevision((version) => version + 1)
          }
        })
        .catch(() => setHasSaveError(true))
    })
    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [draftKey, isFrozen, props.draftStore, props.question])

  useEffect(() => {
    if (!draftKey || !props.isOnlineAuthority || !props.activityRevision) return
    void props.draftStore
      .tombstoneStaleActivity(
        draftKey,
        props.activityRevision,
        activeQuestionKeys.split('\u001f'),
      )
      .catch(() => setHasSaveError(true))
  }, [
    activeQuestionKeys,
    draftKey,
    props.activityRevision,
    props.draftStore,
    props.isOnlineAuthority,
  ])

  useEffect(() => {
    if (!draftLoaded || !matchesEditableFiles(files, props.question)) return
    onFilesChangeRef.current?.(copyFiles(files))
    onValidityChangeRef.current?.(
      Boolean(props.canSubmit !== false && (props.isOnlineAuthority || !draftKey)),
    )
  }, [
    draftKey,
    draftLoaded,
    files,
    props.canSubmit,
    props.isOnlineAuthority,
    props.question,
  ])

  // biome-ignore lint/correctness/useExhaustiveDependencies: Adopted cross-tab generations restart the runtime; local edits are sent through updateFile.
  useEffect(() => {
    if (
      !props.runnerFactory ||
      props.readOnly ||
      props.canSubmit === false ||
      !props.isOnlineAuthority ||
      !draftLoaded ||
      isDraftInvalidated
    ) {
      setPracticeStatus('unavailable')
      setPreviewUrl(null)
      return
    }
    const runner = props.runnerFactory()
    runnerRef.current = runner
    const unsubscribe = runner.subscribe((event) => {
      setPracticeStatus(event.status)
      setPreviewUrl(safePreviewUrl(event.previewUrl))
      setTerminalText(event.terminalText)
    })
    void runner
      .start({
        files: getProjectFiles(files, props.question),
        entrypoint: props.question.entrypoint,
        fixedDependencies: props.question.fixedDependencies,
        permittedCommands: props.question.permittedCommands,
      })
      .catch(() => setPracticeStatus('unavailable'))
    return () => {
      unsubscribe()
      runner.dispose()
      runnerRef.current = null
      setPreviewUrl(null)
    }
    // Restarting on an adopted cross-tab snapshot ensures the preview matches the latest saved generation.
  }, [
    draftLoaded,
    isDraftInvalidated,
    props.isOnlineAuthority,
    props.canSubmit,
    props.question,
    props.readOnly,
    props.runnerFactory,
    runnerRevision,
  ])

  useEffect(
    () => () => {
      if (saveTimeoutRef.current !== null) window.clearTimeout(saveTimeoutRef.current)
      scopeVersionRef.current += 1
    },
    [],
  )

  function handleFileChange(path: string, content: string) {
    if (isFrozen || !props.question.editablePaths.includes(path)) return
    const next = files.map((file) => (file.path === path ? { path, content } : file))
    if (!matchesEditableFiles(next, props.question)) {
      setHasFileError(true)
      return
    }
    setFiles(next)
    filesRef.current = next
    setEditVersion((version) => version + 1)
    setHasFileError(false)
    onFilesChangeRef.current?.(copyFiles(next))
    onValidityChangeRef.current?.(
      Boolean(props.canSubmit !== false && (props.isOnlineAuthority || !draftKey)),
    )
    void runnerRef.current
      ?.updateFile(path, content)
      .catch(() => setPracticeStatus('unavailable'))
  }

  async function handleAssess() {
    if (
      isFrozen ||
      !props.onAssess ||
      !draftLoaded ||
      !matchesEditableFiles(files, props.question) ||
      (draftKey && (!props.isOnlineAuthority || !navigator.onLine))
    )
      return
    setIsAssessing(true)
    setHasAssessError(false)
    const snapshot = copyFiles(filesRef.current)
    try {
      if (draftKey) {
        if (saveTimeoutRef.current !== null) window.clearTimeout(saveTimeoutRef.current)
        await writeQueueRef.current.catch(() => undefined)
        const nextGeneration = await props.draftStore.write(
          draftKey,
          snapshot,
          generationRef.current,
        )
        if (nextGeneration === 0) throw new Error('Draft generation changed')
        generationRef.current = nextGeneration
        setGeneration(nextGeneration)
      }
      await props.onAssess(snapshot)
    } catch {
      setHasAssessError(true)
    } finally {
      setIsAssessing(false)
    }
  }

  return {
    displayFiles: getProjectFiles(files, props.question),
    editablePaths: props.question.editablePaths,
    selectedPath,
    practiceStatus,
    previewUrl,
    terminalText,
    practiceTab,
    isSaving,
    hasSaveError,
    hasFileError,
    hasAssessError,
    isAssessing,
    isFrozen,
    isDraftInvalidated,
    draftLoaded,
    generation,
    handleAssess,
    handleFileChange,
    handleSelectFile: setSelectedPath,
    handleSelectPracticeTab: setPracticeTab,
  }
}

function safePreviewUrl(value: string | null) {
  if (!value) return null
  try {
    const url = new URL(value)
    return url.protocol === 'https:' &&
      url.origin !== window.location.origin &&
      (url.hostname.endsWith('.webcontainer.io') ||
        url.hostname.endsWith('.webcontainer-api.io'))
      ? url.href
      : null
  } catch {
    return null
  }
}
