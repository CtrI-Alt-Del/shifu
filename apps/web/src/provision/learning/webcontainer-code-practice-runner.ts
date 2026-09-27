import type { FileSystemTree, WebContainer, WebContainerProcess } from '@webcontainer/api'

import type {
  CodePracticeEvent,
  CodePracticeProject,
  CodePracticeRunner,
  CodePracticeStatus,
} from '@/core/learning/code-practice-runner'
import { AppError } from '@/core/errors/app-error'

const MAX_SOURCE_BYTES = 256 * 1024
const MAX_OUTPUT_BYTES = 1024 * 1024
const RUN_TIMEOUT_MS = 10_000
const SAFE_PATH = /^(?!\.)(?!.*(?:^|\/)\.\.?\/)(?!.*\\)[a-zA-Z0-9_./-]+$/

let activeContainer: WebContainer | null = null
let activeOwner: symbol | null = null
let bootQueue = Promise.resolve()

export function WebContainerCodePracticeRunner(): CodePracticeRunner {
  const owner = Symbol('code-practice')
  const listeners = new Set<(event: CodePracticeEvent) => void>()
  let container: WebContainer | null = null
  let process: WebContainerProcess | null = null
  let processInputWriter: WritableStreamDefaultWriter<string> | null = null
  let project: CodePracticeProject | null = null
  let latestStdin: string | null = null
  let runId = 0
  let status: CodePracticeStatus = 'idle'
  let disposed = false
  let outputBytes = 0
  let processInputReceived = false
  let editQueue = Promise.resolve()
  let bootPromise = Promise.resolve()
  const sourceByPath = new Map<string, string>()
  let editRevision = 0
  let inputRevision = 0
  let runTimer: ReturnType<typeof setTimeout> | null = null

  function emit(nextStatus: CodePracticeStatus, text: string, currentRunId = runId) {
    if (disposed || currentRunId !== runId) return
    status = nextStatus
    for (const listener of listeners) listener({ status, text, runId: currentRunId })
  }

  function stopProcess() {
    if (runTimer) clearTimeout(runTimer)
    runTimer = null
    process?.kill()
    process = null
    processInputWriter?.releaseLock()
    processInputWriter = null
  }

  function validateProject(nextProject: CodePracticeProject) {
    const paths = new Set<string>()
    let bytes = 0
    for (const file of nextProject.files) {
      if (
        !SAFE_PATH.test(file.path) ||
        file.path.startsWith('/') ||
        file.path
          .split('/')
          .some((segment) => !segment || segment === '.' || segment === '..') ||
        file.path.split('/').some((segment) => segment === 'node_modules') ||
        ['package.json', 'package-lock.json', 'pnpm-lock.yaml'].includes(file.path) ||
        paths.has(file.path)
      ) {
        throw new AppError('Projeto de prática inválido.')
      }
      paths.add(file.path)
      bytes += new TextEncoder().encode(file.content).length
    }
    if (!paths.has(nextProject.entrypoint) || bytes > MAX_SOURCE_BYTES) {
      throw new AppError('Projeto de prática inválido.')
    }
  }

  function findPermittedCommand(nextProject: CodePracticeProject) {
    return nextProject.permittedCommands.find(
      (candidate) =>
        candidate.executable === 'node' &&
        candidate.arguments.length === 1 &&
        candidate.arguments[0] === nextProject.entrypoint,
    )
  }

  function toTree(nextProject: CodePracticeProject): FileSystemTree {
    const tree: FileSystemTree = {}
    for (const file of nextProject.files) {
      const parts = file.path.split('/')
      let branch = tree
      for (const part of parts.slice(0, -1)) {
        if (!branch[part]) branch[part] = { directory: {} }
        const node = branch[part]
        if (!('directory' in node)) throw new AppError('Projeto de prática inválido.')
        branch = node.directory
      }
      branch[parts.at(-1) ?? ''] = { file: { contents: file.content } }
    }
    if (nextProject.fixedDependencies.length) {
      if (tree['package.json']) throw new AppError('Configuração de prática inválida.')
      tree['package.json'] = {
        file: {
          contents: JSON.stringify({
            private: true,
            type: 'commonjs',
            dependencies: Object.fromEntries(
              nextProject.fixedDependencies.map(({ name, version }) => [name, version]),
            ),
          }),
        },
      }
    }
    return tree
  }

  async function streamProcess(
    currentProcess: WebContainerProcess,
    currentRunId: number,
    shouldStop: () => boolean,
  ) {
    const reader = currentProcess.output.getReader()
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done || currentRunId !== runId || disposed || shouldStop()) return
        const remaining = MAX_OUTPUT_BYTES - outputBytes
        if (remaining <= 0) {
          emit('unavailable', 'Saída de prática excedeu o limite.', currentRunId)
          currentProcess.kill()
          return
        }
        const chunk = new TextEncoder().encode(value)
        outputBytes += chunk.length
        emit(
          'running',
          chunk.length > remaining
            ? new TextDecoder().decode(chunk.slice(0, remaining))
            : value,
          currentRunId,
        )
        if (outputBytes >= MAX_OUTPUT_BYTES) {
          emit('unavailable', 'Saída de prática excedeu o limite.', currentRunId)
          currentProcess.kill()
          return
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  async function run(stdin: string | null) {
    if (!container || !project || disposed) return
    stopProcess()
    const currentRunId = ++runId
    outputBytes = 0
    processInputReceived = stdin !== null && stdin.length > 0
    const command = findPermittedCommand(project)
    if (!command) {
      emit('unavailable', '\nComando não permitido.\n', currentRunId)
      return
    }
    emit(
      'running',
      `\n$ ${[command.executable, ...command.arguments].join(' ')}\n`,
      currentRunId,
    )
    let stoppedWhileWaitingForInput = false
    try {
      const currentProcess = await container.spawn(command.executable, [
        ...command.arguments,
      ])
      if (currentRunId !== runId || disposed) {
        currentProcess.kill()
        return
      }
      process = currentProcess
      runTimer = setTimeout(() => {
        if (currentRunId === runId && !disposed) {
          if (!processInputReceived && status !== 'unavailable') {
            stoppedWhileWaitingForInput = true
            emit(
              'waiting-input',
              '\nDigite a entrada padrão para testar sua solução.\n',
              currentRunId,
            )
          } else if (status !== 'unavailable') {
            emit('unavailable', '\nA prática excedeu o limite de tempo.\n', currentRunId)
          }
          if (process === currentProcess) {
            process = null
            processInputWriter?.releaseLock()
            processInputWriter = null
          }
          currentProcess.kill()
        }
      }, RUN_TIMEOUT_MS)
      const stream = streamProcess(
        currentProcess,
        currentRunId,
        () => stoppedWhileWaitingForInput,
      )
      const writer = currentProcess.input.getWriter()
      processInputWriter = writer
      if (stdin !== null && stdin.length > 0) {
        await writer.write(`${stdin.replace(/[\r\n]+$/, '')}\r`)
      }
      const exitCode = await currentProcess.exit
      await stream
      if (
        currentRunId === runId &&
        status !== 'unavailable' &&
        !stoppedWhileWaitingForInput
      ) {
        emit(
          stdin === null ? 'waiting-input' : 'ready',
          exitCode === 0
            ? stdin === null
              ? '\nDigite a entrada padrão para testar sua solução.\n'
              : ''
            : `\nProcesso terminou com código ${exitCode}.\n`,
          currentRunId,
        )
      }
    } catch {
      if (!stoppedWhileWaitingForInput) {
        emit(
          'unavailable',
          'A prática está indisponível. Continue editando e avaliando.',
          currentRunId,
        )
      }
    } finally {
      if (currentRunId === runId) stopProcess()
    }
  }

  return {
    async start(nextProject) {
      if (disposed) return
      try {
        validateProject(nextProject)
        if (!findPermittedCommand(nextProject)) {
          emit('unavailable', '\nComando não permitido.\n')
          return
        }
        project = nextProject
        sourceByPath.clear()
        for (const file of nextProject.files) sourceByPath.set(file.path, file.content)
        emit('booting', 'Iniciando ambiente de prática…')
        const boot = async () => {
          if (disposed) return
          if (activeContainer) activeContainer.teardown()
          activeContainer = null
          activeOwner = null
          const { WebContainer: WebContainerClass } = await import('@webcontainer/api')
          const nextContainer = await WebContainerClass.boot()
          if (disposed) {
            nextContainer.teardown()
            return
          }
          activeContainer = nextContainer
          activeOwner = owner
          container = nextContainer
          await nextContainer.mount(toTree(nextProject))
          if (nextProject.fixedDependencies.length) {
            const install = await nextContainer.spawn(
              'npm',
              ['install', '--ignore-scripts', '--no-audit', '--no-fund'],
              { output: false },
            )
            const timeout = setTimeout(() => install.kill(), RUN_TIMEOUT_MS)
            const installCode = await install.exit
            clearTimeout(timeout)
            if (installCode !== 0) throw new AppError('Dependências indisponíveis.')
          }
          if (editRevision === 0 && latestStdin === null) await run(null)
        }
        const queued = bootQueue.then(boot, boot)
        bootPromise = queued.then(
          () => undefined,
          () => undefined,
        )
        bootQueue = queued.then(
          () => undefined,
          () => undefined,
        )
        await queued
      } catch {
        if (activeOwner === owner) {
          container?.teardown()
          activeContainer = null
          activeOwner = null
          container = null
        }
        emit('unavailable', 'A prática está indisponível. Continue editando e avaliando.')
      }
    },
    async updateFile(path, content) {
      if (!project || !project.files.some((file) => file.path === path && file.editable))
        return
      const totalBytes = [...sourceByPath.entries()].reduce(
        (sum, [filePath, oldContent]) =>
          sum + new TextEncoder().encode(filePath === path ? content : oldContent).length,
        0,
      )
      if (totalBytes > MAX_SOURCE_BYTES) {
        emit('unavailable', 'O arquivo excedeu o limite da prática.')
        return
      }
      sourceByPath.set(path, content)
      const revision = ++editRevision
      ++runId
      stopProcess()
      const update = async () => {
        try {
          await bootPromise
          if (!container || !project) return
          await container.fs.writeFile(path, content)
          if (revision !== editRevision || disposed) return
          await run(latestStdin)
        } catch {
          emit(
            'unavailable',
            'A prática está indisponível. Continue editando e avaliando.',
          )
        }
      }
      editQueue = editQueue.then(update, update)
      await editQueue
    },
    async sendStdin(value) {
      if (!project || disposed) return
      latestStdin = value
      if (process && processInputWriter) {
        await processInputWriter.write(`${value.replace(/[\r\n]+$/, '')}\r`)
        processInputReceived = true
        return
      }
      const revision = ++inputRevision
      ++runId
      stopProcess()
      await bootPromise
      await editQueue
      if (!container || revision !== inputRevision || disposed) return
      await run(latestStdin)
    },
    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    dispose() {
      if (disposed) return
      stopProcess()
      disposed = true
      runId++
      listeners.clear()
      if (activeOwner === owner) {
        container?.teardown()
        activeContainer = null
        activeOwner = null
      }
      container = null
    },
  }
}
