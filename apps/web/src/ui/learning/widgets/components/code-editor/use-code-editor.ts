import { useMemo } from 'react'

export type EditorFile = { path: string; content: string }

export type CodeEditorProps = {
  files: readonly EditorFile[]
  editablePaths?: readonly string[]
  readOnly?: boolean
  selectedPath?: string
  onFileChange?: (path: string, content: string) => void
}

export function useCodeEditor(props: CodeEditorProps) {
  const paths = useMemo(() => new Set(props.editablePaths ?? []), [props.editablePaths])
  const selectedFile =
    props.files.find((file) => file.path === props.selectedPath) ?? props.files[0]
  const isReadOnly = Boolean(
    props.readOnly || !selectedFile || !paths.has(selectedFile.path),
  )

  function handleChange(value: string | undefined) {
    if (!selectedFile || isReadOnly || value === undefined) return

    props.onFileChange?.(selectedFile.path, value)
  }

  return {
    isReadOnly,
    selectedFile,
    selectedPath: selectedFile?.path ?? '',
    handleChange,
  }
}
