import type { ReactFastifyHttpMethod } from './choice-activity'
import type {
  ReactAdditionalFilePolicy,
  ReactPracticeCommand,
  ReactPracticeFile,
} from './react-practice-runner'

export type ReactFastifyPracticeStatus =
  | 'idle'
  | 'starting'
  | 'updating'
  | 'ready'
  | 'error'
  | 'unavailable'

export type ReactFastifyPracticeProject = {
  files: readonly ReactPracticeFile[]
  frontendEntrypoint: string
  apiEntrypoint: string
  fixedDependencies: readonly { name: string; version: string }[]
  permittedCommands: readonly ReactPracticeCommand[]
  frontendCommandId: string
  apiCommandId: string
  additionalFilePolicy?: ReactAdditionalFilePolicy
}

export type ReactFastifyPracticeEvent = {
  frontendStatus: ReactFastifyPracticeStatus
  apiStatus: ReactFastifyPracticeStatus
  previewUrl: string | null
  terminalText: string
}

export type ReactFastifyPracticeHttpRequest = {
  method: ReactFastifyHttpMethod
  path: string
  body?: string
}

export type ReactFastifyPracticeHttpResponse = {
  status: number
  headers: readonly { name: string; value: string }[]
  body: string
  truncated: boolean
}

export type ReactFastifyPracticeRunner = {
  start(project: ReactFastifyPracticeProject): Promise<void>
  updateFile(path: string, content: string): Promise<void>
  addFile(file: ReactPracticeFile): Promise<void>
  request(
    request: ReactFastifyPracticeHttpRequest,
    signal?: AbortSignal,
  ): Promise<ReactFastifyPracticeHttpResponse>
  runCommand(commandId: string): Promise<void>
  restart(): Promise<void>
  subscribe(listener: (event: ReactFastifyPracticeEvent) => void): () => void
  dispose(): void
}
