import type { FileSystemTree, WebContainer, WebContainerProcess } from '@webcontainer/api'

import type {
  ReactPracticeCommand,
  ReactPracticeEvent,
  ReactPracticeFile,
  ReactPracticeProject,
  ReactPracticeRunner,
  ReactPracticeStatus,
} from '@/core/learning/react-practice-runner'
import { AppError } from '@/core/errors/app-error'

const MAX_SOURCE_BYTES = 256 * 1024
const MAX_TERMINAL_BYTES = 1024 * 1024
const INSTALL_TIMEOUT_MS = 180_000
const SAFE_PATH_SEGMENT = /^[a-zA-Z0-9_.-]{1,64}$/
const RESERVED_FILES = new Set([
  'index.html',
  'package.json',
  'package-lock.json',
  'pnpm-lock.yaml',
  'yarn.lock',
  'vite.config.js',
  'vite.config.ts',
  'vite.config.mjs',
  'vite.config.cjs',
])
const DEV_COMMAND = {
  executable: 'npm',
  arguments: ['run', 'dev'],
} as const

export function ReactWebContainerPracticeRunner(): ReactPracticeRunner {
  const listeners = new Set<(event: ReactPracticeEvent) => void>()
  const filesByPath = new Map<string, string>()
  let container: WebContainer | null = null
  let serverProcess: WebContainerProcess | null = null
  let project: ReactPracticeProject | null = null
  let status: ReactPracticeStatus = 'idle'
  let previewUrl: string | null = null
  let terminalText = ''
  let disposed = false
  let terminalBytes = 0
  let bootPromise: Promise<void> = Promise.resolve()
  let fileQueue: Promise<void> = Promise.resolve()
  let installTimer: ReturnType<typeof setTimeout> | null = null

  function emit(nextStatus: ReactPracticeStatus, text = terminalText) {
    if (disposed) return
    status = nextStatus
    terminalText = text
    for (const listener of listeners) listener({ status, previewUrl, terminalText })
  }

  function appendTerminal(text: string) {
    const textBytes = new TextEncoder().encode(text)
    const remainingBytes = MAX_TERMINAL_BYTES - terminalBytes
    if (remainingBytes <= 0) return
    const boundedText =
      textBytes.length > remainingBytes
        ? new TextDecoder().decode(textBytes.slice(0, remainingBytes))
        : text
    terminalBytes += Math.min(textBytes.length, remainingBytes)
    terminalText += boundedText
    emit(status, terminalText)
  }

  function validatePath(path: string) {
    const segments = path.split('/')
    if (
      path.length > 240 ||
      path.startsWith('/') ||
      path.includes('\\') ||
      path.includes('\0') ||
      segments.some(
        (segment) =>
          segment.length === 0 ||
          segment === '.' ||
          segment === '..' ||
          segment.startsWith('.') ||
          !SAFE_PATH_SEGMENT.test(segment),
      ) ||
      segments.some((segment) => RESERVED_FILES.has(segment.toLowerCase()))
    ) {
      throw new AppError('Arquivo de prática inválido.')
    }
  }

  function validateProject(nextProject: ReactPracticeProject) {
    const paths = new Set<string>()
    let sourceBytes = 0
    for (const file of nextProject.files) {
      validatePath(file.path)
      if (paths.has(file.path)) throw new AppError('Projeto de prática inválido.')
      paths.add(file.path)
      sourceBytes += new TextEncoder().encode(file.content).length
    }
    if (
      !paths.has(nextProject.entrypoint) ||
      sourceBytes > MAX_SOURCE_BYTES ||
      !nextProject.fixedDependencies.some(({ name }) => name === 'react') ||
      !nextProject.fixedDependencies.some(({ name }) => name === 'react-dom') ||
      !nextProject.fixedDependencies.some(({ name }) => name === 'vite')
    ) {
      throw new AppError('Projeto React de prática inválido.')
    }
    const policy = nextProject.additionalFilePolicy
    if (
      policy &&
      (!Number.isInteger(policy.maxFiles) || policy.maxFiles < 1 || policy.maxFiles > 32)
    ) {
      throw new AppError('Política de arquivos de prática inválida.')
    }
  }

  function findDevCommand(
    nextProject: ReactPracticeProject,
  ): ReactPracticeCommand | null {
    return (
      nextProject.permittedCommands.find(
        (command) =>
          command.executable === DEV_COMMAND.executable &&
          command.arguments.length === DEV_COMMAND.arguments.length &&
          command.arguments.every(
            (argument, index) => argument === DEV_COMMAND.arguments[index],
          ),
      ) ?? null
    )
  }

  function toTree(): FileSystemTree {
    if (!project) throw new AppError('Projeto React de prática indisponível.')
    const tree: FileSystemTree = {}
    for (const [path, content] of filesByPath.entries()) {
      const segments = path.split('/')
      let branch = tree
      for (const segment of segments.slice(0, -1)) {
        const node = branch[segment]
        if (node && !('directory' in node)) {
          throw new AppError('Projeto React de prática inválido.')
        }
        if (!node) branch[segment] = { directory: {} }
        branch = (branch[segment] as { directory: FileSystemTree }).directory
      }
      const filename = segments.at(-1)
      if (!filename) throw new AppError('Projeto React de prática inválido.')
      branch[filename] = { file: { contents: content } }
    }

    const dependencies = Object.fromEntries(
      project.fixedDependencies.map(({ name, version }) => [name, version]),
    )
    tree['package.json'] = {
      file: {
        contents: JSON.stringify({
          private: true,
          type: 'module',
          scripts: { dev: 'vite --host 0.0.0.0' },
          dependencies,
        }),
      },
    }
    tree['vite.config.js'] = {
      file: {
        contents: "export default { server: { host: '0.0.0.0', strictPort: true } }\n",
      },
    }
    tree['index.html'] = {
      file: {
        contents: [
          '<!doctype html>',
          '<html lang="pt-BR">',
          '<head>',
          '  <meta charset="UTF-8">',
          '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
          '  <title>Prática React</title>',
          '</head>',
          '<body>',
          '  <div id="root"></div>',
          `  <script type="module" src="/${project.entrypoint}"></script>`,
          '</body>',
          '</html>',
        ].join('\n'),
      },
    }
    return tree
  }

  function validateAdditionalFile(file: ReactPracticeFile) {
    validatePath(file.path)
    const policy = project?.additionalFilePolicy
    if (!policy || filesByPath.has(file.path)) {
      throw new AppError('Este arquivo não pode ser adicionado à prática.')
    }
    const extensionIndex = file.path.lastIndexOf('.')
    const extension =
      extensionIndex < 0 ? '' : file.path.slice(extensionIndex).toLowerCase()
    const isAllowedDirectory = policy.allowedDirectories.some((allowedDirectory) =>
      file.path.startsWith(`${allowedDirectory}/`),
    )
    const additionalFilesCount = [...filesByPath.keys()].filter(
      (path) => !project?.files.some((initialFile) => initialFile.path === path),
    ).length
    const totalBytes = [...filesByPath.entries()].reduce(
      (total, [path, content]) =>
        total +
        new TextEncoder().encode(path === file.path ? file.content : content).length,
      new TextEncoder().encode(file.content).length,
    )
    if (
      !isAllowedDirectory ||
      !policy.allowedExtensions.some(
        (allowedExtension) => extension === allowedExtension.toLowerCase(),
      ) ||
      additionalFilesCount >= policy.maxFiles ||
      totalBytes > MAX_SOURCE_BYTES
    ) {
      throw new AppError('Este arquivo não atende à política de prática.')
    }
  }

  async function streamServerOutput(process: WebContainerProcess) {
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

  async function boot(nextProject: ReactPracticeProject) {
    const command = findDevCommand(nextProject)
    if (!command) {
      emit(
        'unavailable',
        'Prévia indisponível: o comando de desenvolvimento não foi autorizado.',
      )
      return
    }
    if (!window.isSecureContext || !window.crossOriginIsolated) {
      emit(
        'unavailable',
        'Prévia indisponível neste navegador. Continue editando e avaliando.',
      )
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
      await nextContainer.mount(toTree())
      const installProcess = await nextContainer.spawn(
        'npm',
        ['install', '--ignore-scripts', '--no-audit', '--no-fund'],
        { output: false },
      )
      installTimer = setTimeout(() => installProcess.kill(), INSTALL_TIMEOUT_MS)
      const installExitCode = await installProcess.exit
      if (installTimer) clearTimeout(installTimer)
      installTimer = null
      if (disposed) return
      if (installExitCode !== 0) throw new AppError('Dependências React indisponíveis.')

      nextContainer.on('server-ready', (_port, url) => {
        if (disposed) return
        try {
          const readyUrl = new URL(url)
          if (
            readyUrl.protocol !== 'https:' ||
            readyUrl.origin === window.location.origin ||
            (!readyUrl.hostname.endsWith('.webcontainer.io') &&
              !readyUrl.hostname.endsWith('.webcontainer-api.io'))
          ) {
            emit('unavailable', 'Prévia indisponível: origem isolada não confirmada.')
            return
          }
          previewUrl = readyUrl.toString()
          emit('ready')
        } catch {
          emit('unavailable', 'Prévia indisponível: endereço do servidor inválido.')
        }
      })
      serverProcess = await nextContainer.spawn(command.executable, [
        ...command.arguments,
      ])
      void streamServerOutput(serverProcess)
      void serverProcess.exit.then((exitCode) => {
        if (!disposed && status !== 'unavailable') {
          previewUrl = null
          emit('unavailable', `Servidor de prática encerrado (código ${exitCode}).`)
        }
      })
    } catch {
      if (!disposed) {
        serverProcess?.kill()
        serverProcess = null
        container?.teardown()
        container = null
        previewUrl = null
        emit('unavailable', 'A prévia está indisponível. Continue editando e avaliando.')
      }
    }
  }

  function enqueueFileWrite(file: ReactPracticeFile) {
    const write = async () => {
      await bootPromise
      if (disposed || !container) return
      const parentDirectory = file.path.slice(0, file.path.lastIndexOf('/'))
      if (parentDirectory) await container.fs.mkdir(parentDirectory, { recursive: true })
      await container.fs.writeFile(file.path, file.content)
    }
    fileQueue = fileQueue.then(write, write)
    return fileQueue
  }

  return {
    async start(nextProject) {
      if (disposed || status !== 'idle') return
      try {
        validateProject(nextProject)
        project = nextProject
        filesByPath.clear()
        for (const file of nextProject.files) filesByPath.set(file.path, file.content)
        terminalBytes = 0
        terminalText = ''
        previewUrl = null
        emit('booting', 'Iniciando ambiente React de prática…\n')
        bootPromise = boot(nextProject)
        await bootPromise
      } catch {
        emit('unavailable', 'A prévia está indisponível. Continue editando e avaliando.')
      }
    },
    async updateFile(path, content) {
      if (disposed || !project || !filesByPath.has(path)) return
      const totalBytes = [...filesByPath.entries()].reduce(
        (total, [filePath, previousContent]) =>
          total +
          new TextEncoder().encode(filePath === path ? content : previousContent).length,
        0,
      )
      if (totalBytes > MAX_SOURCE_BYTES) {
        appendTerminal('\nArquivo excede o limite de prática de 256 KiB.\n')
        return
      }
      filesByPath.set(path, content)
      await enqueueFileWrite({ path, content })
    },
    async addFile(file) {
      if (disposed || !project) return
      validateAdditionalFile(file)
      filesByPath.set(file.path, file.content)
      await enqueueFileWrite(file)
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
