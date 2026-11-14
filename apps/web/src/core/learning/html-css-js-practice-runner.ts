export type HtmlCssJsPracticeFile = { path: string; content: string }

export type HtmlCssJsPracticeCommand = {
  id: string
  executable: string
  arguments: readonly string[]
}

export type HtmlCssJsPracticeProject = {
  files: readonly HtmlCssJsPracticeFile[]
  entrypoint: string
  fixedDependencies: readonly { name: string; version: string }[]
  permittedCommands: readonly HtmlCssJsPracticeCommand[]
}

export type HtmlCssJsPracticeStatus = 'idle' | 'booting' | 'ready' | 'unavailable'

export type HtmlCssJsPracticeEvent = {
  status: HtmlCssJsPracticeStatus
  previewUrl: string | null
  terminalText: string
}

export type HtmlCssJsPracticeRunner = {
  start(project: HtmlCssJsPracticeProject): Promise<void>
  updateFile(path: string, content: string): Promise<void>
  subscribe(listener: (event: HtmlCssJsPracticeEvent) => void): () => void
  dispose(): void
}
