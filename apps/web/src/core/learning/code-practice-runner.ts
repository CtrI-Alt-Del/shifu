export type CodeProjectFile = {
  path: string
  content: string
  editable: boolean
}

export type CodePracticeCommand = {
  id: string
  executable: string
  arguments: readonly string[]
}

export type CodePracticeProject = {
  files: readonly CodeProjectFile[]
  entrypoint: string
  fixedDependencies: readonly { name: string; version: string }[]
  permittedCommands: readonly CodePracticeCommand[]
}

export type CodePracticeStatus =
  | 'idle'
  | 'booting'
  | 'waiting-input'
  | 'running'
  | 'ready'
  | 'unavailable'

export type CodePracticeEvent = {
  status: CodePracticeStatus
  text: string
  runId: number
}

export type CodePracticeRunner = {
  start(project: CodePracticeProject): Promise<void>
  updateFile(path: string, content: string): Promise<void>
  sendStdin(text: string): Promise<void>
  subscribe(listener: (event: CodePracticeEvent) => void): () => void
  dispose(): void
}
