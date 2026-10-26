import type { FileSystemTree, WebContainer, WebContainerProcess } from '@webcontainer/api'
import { AppError } from '@/core/errors/app-error'
import type {
  HtmlCssJsPracticeEvent,
  HtmlCssJsPracticeProject,
  HtmlCssJsPracticeRunner,
} from '@/core/learning/html-css-js-practice-runner'

const MAX_SOURCE_BYTES = 256 * 1024
const MAX_TERMINAL_BYTES = 1024 * 1024
const INSTALL_TIMEOUT_MS = 180_000
const SAFE_PATH_SEGMENT = /^[a-zA-Z0-9_.-]{1,64}$/
const START_COMMAND = {
  executable: 'npm',
  arguments: ['run', 'dev'],
} as const

export function HtmlCssJsWebContainerPracticeRunner(): HtmlCssJsPracticeRunner {
  const listeners = new Set<(event: HtmlCssJsPracticeEvent) => void>()
  const filesByPath = new Map<string, string>()
  let container: WebContainer | null = null
  let serverProcess: WebContainerProcess | null = null
  let status: HtmlCssJsPracticeEvent['status'] = 'idle'
  let previewUrl: string | null = null
  let terminalText = ''
  let disposed = false
  let terminalBytes = 0
  let installTimer: ReturnType<typeof setTimeout> | null = null
  let fileQueue: Promise<void> = Promise.resolve()

  function emit(nextStatus: HtmlCssJsPracticeEvent['status']) {
    if (disposed) return
    status = nextStatus
    for (const listener of listeners) listener({ status, previewUrl, terminalText })
  }

  function appendTerminal(text: string) {
    const encoded = new TextEncoder().encode(text)
    const remaining = MAX_TERMINAL_BYTES - terminalBytes
    if (remaining <= 0) return
    const bounded =
      encoded.length > remaining
        ? new TextDecoder().decode(encoded.slice(0, remaining))
        : text
    terminalBytes += Math.min(encoded.length, remaining)
    terminalText += bounded
    emit(status)
  }

  function validatePath(path: string) {
    const segments = path.split('/')
    if (
      !path ||
      path.length > 240 ||
      path.startsWith('/') ||
      path.includes('\\') ||
      path.includes('\0') ||
      segments.some(
        (segment) =>
          segment === '' ||
          segment === '.' ||
          segment === '..' ||
          segment.startsWith('.') ||
          !SAFE_PATH_SEGMENT.test(segment),
      )
    )
      throw new AppError('Arquivo de prática inválido.')
  }

  function validateProject(project: HtmlCssJsPracticeProject) {
    const paths = new Set<string>()
    let sourceBytes = 0
    for (const file of project.files) {
      validatePath(file.path)
      if (paths.has(file.path)) throw new AppError('Projeto de prática inválido.')
      paths.add(file.path)
      sourceBytes += new TextEncoder().encode(file.path).byteLength
      sourceBytes += new TextEncoder().encode(file.content).byteLength
    }
    if (!paths.has(project.entrypoint) || sourceBytes > MAX_SOURCE_BYTES) {
      throw new AppError('Projeto de página web de prática inválido.')
    }
    if (
      [...paths].some((path) =>
        ['package.json', 'package-lock.json', 'pnpm-lock.yaml'].includes(
          path.toLowerCase(),
        ),
      )
    ) {
      throw new AppError('O projeto não pode substituir a configuração da prática.')
    }
  }

  function hasAuthorizedStart(project: HtmlCssJsPracticeProject) {
    return (
      project.fixedDependencies.some(({ name }) => name === 'vite') &&
      project.permittedCommands.some(
        (command) =>
          command.executable === START_COMMAND.executable &&
          command.arguments.length === START_COMMAND.arguments.length &&
          command.arguments.every(
            (argument, index) => argument === START_COMMAND.arguments[index],
          ),
      )
    )
  }

  function toTree(project: HtmlCssJsPracticeProject): FileSystemTree {
    const tree: FileSystemTree = {}
    for (const [path, content] of filesByPath) {
      let branch = tree
      const segments = path.split('/')
      for (const segment of segments.slice(0, -1)) {
        const node = branch[segment]
        if (node && !('directory' in node))
          throw new AppError('Projeto de prática inválido.')
        if (!node) branch[segment] = { directory: {} }
        branch = (branch[segment] as { directory: FileSystemTree }).directory
      }
      const name = segments.at(-1)
      if (!name) throw new AppError('Projeto de prática inválido.')
      branch[name] = { file: { contents: content } }
    }
    tree['package.json'] = {
      file: {
        contents: JSON.stringify({
          private: true,
          type: 'module',
          scripts: { dev: 'vite --host 0.0.0.0' },
          dependencies: Object.fromEntries(
            project.fixedDependencies.map(({ name, version }) => [name, version]),
          ),
        }),
      },
    }
    return tree
  }

  async function streamOutput(process: WebContainerProcess) {
    const reader = process.output.getReader()
    try {
      while (!disposed) {
        const { done, value } = await reader.read()
        if (done) return
        appendTerminal(value)
      }
    } catch {
      if (!disposed)
        appendTerminal('\nA saída do servidor de prática foi interrompida.\n')
    } finally {
      reader.releaseLock()
    }
  }

  async function boot(project: HtmlCssJsPracticeProject) {
    if (!hasAuthorizedStart(project)) {
      appendTerminal(
        'Prévia indisponível: o comando de desenvolvimento não foi autorizado. Continue editando e avaliando.\n',
      )
      emit('unavailable')
      return
    }
    if (!window.isSecureContext || !window.crossOriginIsolated) {
      appendTerminal(
        'Prévia indisponível neste navegador. Continue editando e avaliando.\n',
      )
      emit('unavailable')
      return
    }
    try {
      const { WebContainer: WebContainerClass } = await import('@webcontainer/api')
      if (disposed) return
      const nextContainer = await WebContainerClass.boot()
      container = nextContainer
      if (disposed) {
        nextContainer.teardown()
        container = null
        return
      }
      await nextContainer.mount(toTree(project))
      const install = await nextContainer.spawn(
        'npm',
        ['install', '--ignore-scripts', '--no-audit', '--no-fund'],
        { output: false },
      )
      installTimer = setTimeout(() => install.kill(), INSTALL_TIMEOUT_MS)
      const installExitCode = await install.exit
      if (installTimer) clearTimeout(installTimer)
      installTimer = null
      if (disposed) return
      if (installExitCode !== 0)
        throw new AppError('Dependências fixas de prática indisponíveis.')
      nextContainer.on('server-ready', (_port, url) => {
        if (disposed) return
        try {
          const parsed = new URL(url)
          if (
            parsed.protocol !== 'https:' ||
            parsed.origin === window.location.origin ||
            (!parsed.hostname.endsWith('.webcontainer.io') &&
              !parsed.hostname.endsWith('.webcontainer-api.io'))
          ) {
            previewUrl = null
            appendTerminal('Prévia indisponível: origem isolada não confirmada.\n')
            emit('unavailable')
            return
          }
          const entrypoint = project.entrypoint
            .split('/')
            .map((segment) => encodeURIComponent(segment))
            .join('/')
          previewUrl = new URL(entrypoint, parsed).href
          emit('ready')
        } catch {
          appendTerminal('Prévia indisponível: endereço do servidor inválido.\n')
          emit('unavailable')
        }
      })
      serverProcess = await nextContainer.spawn(START_COMMAND.executable, [
        ...START_COMMAND.arguments,
      ])
      void streamOutput(serverProcess)
      void serverProcess.exit.then((code) => {
        if (disposed || status === 'unavailable') return
        previewUrl = null
        appendTerminal(`Servidor de prática encerrado (código ${code}).\n`)
        emit('unavailable')
      })
    } catch {
      if (!disposed) {
        serverProcess?.kill()
        serverProcess = null
        container?.teardown()
        container = null
        previewUrl = null
        appendTerminal('A prévia está indisponível. Continue editando e avaliando.\n')
        emit('unavailable')
      }
    }
  }

  return {
    async start(project) {
      if (disposed || status !== 'idle') return
      try {
        validateProject(project)
        filesByPath.clear()
        for (const file of project.files) filesByPath.set(file.path, file.content)
        terminalBytes = 0
        terminalText = ''
        previewUrl = null
        emit('booting')
        await boot(project)
      } catch {
        appendTerminal('A prévia está indisponível. Continue editando e avaliando.\n')
        emit('unavailable')
      }
    },
    async updateFile(path, content) {
      if (disposed || !filesByPath.has(path)) return
      const size = [...filesByPath].reduce(
        (total, [currentPath, previous]) =>
          total +
          new TextEncoder().encode(currentPath).byteLength +
          new TextEncoder().encode(currentPath === path ? content : previous).byteLength,
        0,
      )
      if (size > MAX_SOURCE_BYTES) {
        appendTerminal('Projeto acima do limite de prática de 256 KiB.\n')
        return
      }
      filesByPath.set(path, content)
      const write = async () => {
        if (disposed || !container) return
        const parent = path.slice(0, path.lastIndexOf('/'))
        if (parent) await container.fs.mkdir(parent, { recursive: true })
        await container.fs.writeFile(path, content)
      }
      fileQueue = fileQueue.then(write, write)
      await fileQueue
    },
    subscribe(listener) {
      listeners.add(listener)
      listener({ status, previewUrl, terminalText })
      return () => listeners.delete(listener)
    },
    dispose() {
      if (disposed) return
      disposed = true
      if (installTimer) clearTimeout(installTimer)
      installTimer = null
      serverProcess?.kill()
      serverProcess = null
      container?.teardown()
      container = null
      previewUrl = null
      listeners.clear()
    },
  }
}
