import { useCallback } from 'react'

type ActivityFile = { path: string; content: string }
type MutableReference<Value> = { current: Value }
type StateSetter<Value> = (value: Value | ((previousValue: Value) => Value)) => void

type AccountActivityDraftRevocationDependencies = {
  initialFiles: ActivityFile[]
  isAccountRevokedRef: MutableReference<boolean>
  isDraftInvalidatedRef: MutableReference<boolean>
  filesRef: MutableReference<ActivityFile[]>
  onFilesChangeRef: MutableReference<
    ((files: readonly ActivityFile[]) => void) | undefined
  >
  onAnswerValidityChangeRef: MutableReference<((isValid: boolean) => void) | undefined>
  setDraftLoaded: StateSetter<boolean>
  setFiles: StateSetter<ActivityFile[]>
  setSelectedPath: StateSetter<string>
  setIsDraftInvalidated: StateSetter<boolean>
}

type AccountActivityDraftRevocationOptions = {
  selectedPath?: string
  updateFilesRef?: boolean
}

export function useAccountActivityDraftRevocation({
  filesRef,
  initialFiles,
  isAccountRevokedRef,
  isDraftInvalidatedRef,
  onAnswerValidityChangeRef,
  onFilesChangeRef,
  setDraftLoaded,
  setFiles,
  setIsDraftInvalidated,
  setSelectedPath,
}: AccountActivityDraftRevocationDependencies) {
  return useCallback(
    function handleAccountActivityDraftRevocation({
      selectedPath = initialFiles[0]?.path ?? '',
      updateFilesRef = false,
    }: AccountActivityDraftRevocationOptions = {}) {
      isAccountRevokedRef.current = true
      isDraftInvalidatedRef.current = true
      setIsDraftInvalidated(true)
      setDraftLoaded(true)
      setFiles(initialFiles)
      if (updateFilesRef) filesRef.current = initialFiles
      setSelectedPath(selectedPath)
      onFilesChangeRef.current?.(
        initialFiles.map(({ path, content }) => ({ path, content })),
      )
      onAnswerValidityChangeRef.current?.(false)
    },
    [
      filesRef,
      initialFiles,
      isAccountRevokedRef,
      isDraftInvalidatedRef,
      onAnswerValidityChangeRef,
      onFilesChangeRef,
      setDraftLoaded,
      setFiles,
      setIsDraftInvalidated,
      setSelectedPath,
    ],
  )
}
