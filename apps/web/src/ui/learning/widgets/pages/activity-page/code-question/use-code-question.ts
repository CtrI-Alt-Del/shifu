import { useEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent, PointerEvent } from 'react'
import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import type {
  CodePracticeProject,
  CodePracticeRunner,
  CodePracticeStatus,
} from '@/core/learning/code-practice-runner'

export type CodeQuestionProps = {
  activityTitle?: string
  difficulty?: ActivityDifficulty
  questionNumber?: number
  totalQuestions?: number
  question: {
    key: string
    prompt: string
    initialFiles: readonly { path: string; content: string; editable: boolean }[]
    entrypoint: string
    editablePaths: readonly string[]
    fixedDependencies: readonly { name: string; version: string }[]
    permittedCommands: readonly {
      id: string
      executable: string
      arguments: readonly string[]
    }[]
    criteria?: readonly { key: string; name: string; weightPercentage: number }[]
  }
  readOnly?: boolean
  disabled?: boolean
  onFilesChange?: (files: readonly { path: string; content: string }[]) => void
  onAssess?: (files: readonly { path: string; content: string }[]) => void | Promise<void>
  runnerFactory?: () => CodePracticeRunner
}

type ResizePanel = 'sidebar' | 'editor'

const HANDLE_WIDTH = 8
const SIDEBAR_MIN_WIDTH = 220
const EDITOR_MIN_WIDTH = 280
const TERMINAL_MIN_WIDTH = 240
const RESIZE_STEP = 16

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum)
}

export function useCodeQuestion(props: CodeQuestionProps) {
  const { question } = props
  const [files, setFiles] = useState(() =>
    question.initialFiles.map(({ path, content }) => ({ path, content })),
  )
  const [selectedPanel, setSelectedPanel] = useState<'prompt' | 'files'>('prompt')
  const [selectedPath, setSelectedPath] = useState(question.initialFiles[0]?.path ?? '')
  const [practiceStatus, setPracticeStatus] = useState<CodePracticeStatus>('idle')
  const [isAssessing, setIsAssessing] = useState(false)
  const [hasAssessError, setHasAssessError] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(280)
  const [editorWidth, setEditorWidth] = useState<number | null>(null)
  const [workspaceWidth, setWorkspaceWidth] = useState(0)
  const [editorGridWidth, setEditorGridWidth] = useState(0)
  const workspaceRef = useRef<HTMLDivElement>(null)
  const editorGridRef = useRef<HTMLDivElement>(null)
  const resizeRef = useRef<{
    panel: ResizePanel
    startX: number
    startWidth: number
  } | null>(null)
  const assessingRef = useRef(false)
  const runnerRef = useRef<CodePracticeRunner | null>(null)
  const runnerFactoryRef = useRef(props.runnerFactory)
  const initialProjectRef = useRef({
    key: question.key,
    project: {
      files: question.initialFiles,
      entrypoint: question.entrypoint,
      fixedDependencies: question.fixedDependencies,
      permittedCommands: question.permittedCommands,
    } satisfies CodePracticeProject,
  })
  if (initialProjectRef.current.key !== question.key) {
    initialProjectRef.current = {
      key: question.key,
      project: {
        files: question.initialFiles,
        entrypoint: question.entrypoint,
        fixedDependencies: question.fixedDependencies,
        permittedCommands: question.permittedCommands,
      },
    }
  }
  const editablePaths = useMemo(
    () =>
      new Set(
        question.initialFiles
          .filter((file) => file.editable && question.editablePaths.includes(file.path))
          .map((file) => file.path),
      ),
    [question.editablePaths, question.initialFiles],
  )
  const isFrozen = Boolean(props.readOnly || props.disabled || isAssessing)

  useEffect(() => {
    if (props.readOnly || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(() => {
      setWorkspaceWidth(workspaceRef.current?.clientWidth ?? 0)
      setEditorGridWidth(editorGridRef.current?.clientWidth ?? 0)
    })
    if (workspaceRef.current) observer.observe(workspaceRef.current)
    if (editorGridRef.current) observer.observe(editorGridRef.current)
    return () => observer.disconnect()
  }, [props.readOnly])

  const sidebarMaximum = Math.max(
    280,
    workspaceWidth - HANDLE_WIDTH * 2 - EDITOR_MIN_WIDTH - TERMINAL_MIN_WIDTH,
  )
  const editorMaximum = Math.max(
    EDITOR_MIN_WIDTH,
    editorGridWidth - HANDLE_WIDTH - TERMINAL_MIN_WIDTH,
  )
  const currentSidebarWidth = clamp(sidebarWidth, SIDEBAR_MIN_WIDTH, sidebarMaximum)
  const currentEditorWidth = clamp(
    editorWidth ?? Math.round((editorGridWidth - HANDLE_WIDTH) * 0.55),
    EDITOR_MIN_WIDTH,
    editorMaximum,
  )

  function getPanelWidth(panel: ResizePanel) {
    const grid = panel === 'sidebar' ? workspaceRef.current : editorGridRef.current
    const measured = grid?.firstElementChild?.getBoundingClientRect().width
    if (measured && measured > 0) return measured
    return panel === 'sidebar' ? currentSidebarWidth : currentEditorWidth
  }

  function getPanelBounds(panel: ResizePanel) {
    const gridWidth =
      (panel === 'sidebar' ? workspaceRef.current : editorGridRef.current)?.clientWidth ??
      0
    const minimum = panel === 'sidebar' ? SIDEBAR_MIN_WIDTH : EDITOR_MIN_WIDTH
    const maximum = Math.max(
      minimum,
      gridWidth -
        (panel === 'sidebar' ? HANDLE_WIDTH * 2 + EDITOR_MIN_WIDTH : HANDLE_WIDTH) -
        TERMINAL_MIN_WIDTH,
    )
    return { minimum, maximum, gridWidth }
  }

  function setPanelWidth(panel: ResizePanel, width: number) {
    const { minimum, maximum, gridWidth } = getPanelBounds(panel)
    const nextWidth = clamp(Math.round(width), minimum, maximum)
    if (panel === 'sidebar') {
      setWorkspaceWidth(gridWidth)
      setSidebarWidth(nextWidth)
      setEditorGridWidth(Math.max(0, gridWidth - nextWidth - HANDLE_WIDTH))
    } else {
      setEditorGridWidth(gridWidth)
      setEditorWidth(nextWidth)
    }
  }

  function handleResizePointerDown(
    panel: ResizePanel,
    event: PointerEvent<HTMLDivElement>,
  ) {
    if (event.button !== 0) return
    event.currentTarget.focus()
    event.currentTarget.setPointerCapture(event.pointerId)
    resizeRef.current = {
      panel,
      startX: event.clientX,
      startWidth: getPanelWidth(panel),
    }
    event.preventDefault()
  }

  function handleResizePointerMove(
    panel: ResizePanel,
    event: PointerEvent<HTMLDivElement>,
  ) {
    const resize = resizeRef.current
    if (!resize || resize.panel !== panel) return
    setPanelWidth(panel, resize.startWidth + event.clientX - resize.startX)
  }

  function handleResizePointerEnd(event: PointerEvent<HTMLDivElement>) {
    if (!resizeRef.current) return
    resizeRef.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  function handleResizeKeyDown(panel: ResizePanel, event: KeyboardEvent<HTMLDivElement>) {
    const { minimum, maximum } = getPanelBounds(panel)
    const step = event.shiftKey ? RESIZE_STEP * 3 : RESIZE_STEP
    const nextWidth =
      event.key === 'Home'
        ? minimum
        : event.key === 'End'
          ? maximum
          : event.key === 'ArrowLeft'
            ? getPanelWidth(panel) - step
            : event.key === 'ArrowRight'
              ? getPanelWidth(panel) + step
              : null
    if (nextWidth === null) return
    event.preventDefault()
    setPanelWidth(panel, nextWidth)
  }

  useEffect(() => {
    if (initialProjectRef.current.key !== question.key) return
    if (props.readOnly) return
    const runnerFactory = runnerFactoryRef.current
    if (!runnerFactory) {
      setPracticeStatus('unavailable')
      return
    }
    const runner = runnerFactory()
    runnerRef.current = runner
    const unsubscribe = runner.subscribe((event) => setPracticeStatus(event.status))
    void runner.start(initialProjectRef.current.project)
    return () => {
      unsubscribe()
      runner.dispose()
      runnerRef.current = null
    }
  }, [question.key, props.readOnly])

  function handleFileChange(path: string, content: string) {
    if (isFrozen || !editablePaths.has(path)) return
    const nextFiles = files.map((file) => (file.path === path ? { path, content } : file))
    setFiles(nextFiles)
    const submitted = nextFiles.filter((file) => editablePaths.has(file.path))
    props.onFilesChange?.(submitted)
    void runnerRef.current?.updateFile(path, content)
  }

  async function handleAssess() {
    if (isFrozen || assessingRef.current || !props.onAssess) return
    assessingRef.current = true
    setIsAssessing(true)
    setHasAssessError(false)
    const snapshot = files
      .filter((file) => editablePaths.has(file.path))
      .map((file) => ({ ...file }))
    try {
      await props.onAssess(snapshot)
    } catch {
      setHasAssessError(true)
    } finally {
      assessingRef.current = false
      setIsAssessing(false)
    }
  }

  function handleSelectPanel(panel: 'prompt' | 'files') {
    setSelectedPanel(panel)
  }

  function handleSelectFile(path: string) {
    if (files.some((file) => file.path === path)) setSelectedPath(path)
  }

  return {
    files,
    editablePaths: [...editablePaths],
    hasAssessError,
    isAssessing,
    isFrozen,
    practiceStatus,
    runner: runnerRef.current,
    selectedPanel,
    selectedPath,
    sidebarWidth: currentSidebarWidth,
    editorWidth: editorWidth === null ? null : currentEditorWidth,
    resizeValues: {
      sidebar: {
        minimum: SIDEBAR_MIN_WIDTH,
        maximum: sidebarMaximum,
        current: currentSidebarWidth,
      },
      editor: {
        minimum: EDITOR_MIN_WIDTH,
        maximum: editorMaximum,
        current: currentEditorWidth,
      },
    },
    workspaceRef,
    editorGridRef,
    handleAssess,
    handleFileChange,
    handleSelectFile,
    handleSelectPanel,
    handleResizePointerDown,
    handleResizePointerMove,
    handleResizePointerEnd,
    handleResizeKeyDown,
  }
}
