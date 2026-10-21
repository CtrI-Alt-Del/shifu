export type ReactPracticeFile = {
  path: string
  content: string
}

export type ReactAdditionalFilePolicy = {
  allowedDirectories: readonly string[]
  allowedExtensions: readonly string[]
  maxFiles: number
}

export type ReactPracticeCommand = {
  id: string
  executable: string
  arguments: readonly string[]
}

export type ReactPracticeProject = {
  files: readonly ReactPracticeFile[]
  entrypoint: string
  fixedDependencies: readonly { name: string; version: string }[]
  permittedCommands: readonly ReactPracticeCommand[]
  additionalFilePolicy?: ReactAdditionalFilePolicy
}

export type ReactPracticeStatus = 'idle' | 'booting' | 'ready' | 'unavailable'

export type ReactPracticeEvent = {
  status: ReactPracticeStatus
  previewUrl: string | null
  terminalText: string
}

export type ReactPracticeRunner = {
  start(project: ReactPracticeProject): Promise<void>
  updateFile(path: string, content: string): Promise<void>
  addFile(file: ReactPracticeFile): Promise<void>
  subscribe(listener: (event: ReactPracticeEvent) => void): () => void
  dispose(): void
}
